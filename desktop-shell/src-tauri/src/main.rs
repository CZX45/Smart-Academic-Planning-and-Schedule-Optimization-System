#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Deserialize;
use std::fs;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};
use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

#[derive(Debug, Deserialize)]
struct RuntimeManifest {
    base_url: String,
    pid: u32,
    port: u16,
    status: String,
}

#[derive(Default)]
struct Processes {
    api: Option<Child>,
    web: Option<Child>,
    manifest: Option<PathBuf>,
}

#[derive(Default)]
struct DesktopProcesses(Mutex<Processes>);

impl DesktopProcesses {
    fn start(&self) -> Result<RuntimeManifest, String> {
        let mut guard = self.0.lock().map_err(|_| "process lock poisoned")?;
        if guard
            .api
            .as_mut()
            .is_some_and(|child| child.try_wait().ok().flatten().is_none())
        {
            return Err("The API child is already running".to_string());
        }
        if guard
            .web
            .as_mut()
            .is_some_and(|child| child.try_wait().ok().flatten().is_none())
        {
            return Err("The Web child is already running".to_string());
        }

        let repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(Path::parent)
            .ok_or_else(|| "Could not locate repository root".to_string())?
            .to_path_buf();
        let api_directory = repo_root.join("apps").join("api");
        let local_app_data = proof_local_app_data();
        let app_data = local_app_data.join("SAPSOS");
        fs::create_dir_all(&app_data)
            .map_err(|error| format!("Could not create proof app-data directory: {error}"))?;
        let database_path = app_data.join("tauri-proof.db");
        let database_url = format!(
            "sqlite+pysqlite:///{}",
            database_path.to_string_lossy().replace('\\', "/")
        );

        let packaged_api = std::env::var_os("SAPSOS_API_EXECUTABLE").map(PathBuf::from);
        let (api_executable, api_arguments, api_working_directory) = if let Some(path) =
            packaged_api
        {
            if !path.is_file() {
                return Err(format!(
                    "Packaged FastAPI artifact was not found at {}. Build it with scripts/windows/Build-FastAPI-Runtime.ps1.",
                    path.display()
                ));
            }
            let working_directory = path
                .parent()
                .ok_or_else(|| "Packaged FastAPI artifact has no parent directory".to_string())?
                .to_path_buf();
            (path, Vec::new(), working_directory)
        } else {
            (
                PathBuf::from(std::env::var("PYTHON").unwrap_or_else(|_| "python".to_string())),
                vec!["-m".to_string(), "app.run".to_string()],
                api_directory.clone(),
            )
        };
        let api_child = Command::new(api_executable)
            .args(api_arguments)
            .current_dir(api_working_directory)
            .env("LOCALAPPDATA", &local_app_data)
            .env("DATABASE_URL", database_url)
            .env("PRODUCT_MODE", "LOCAL_DESKTOP")
            .env("AUTH_MODE", "local")
            .env("ENVIRONMENT", "test")
            .env("API_HOST", "127.0.0.1")
            .env("API_PORT", "0")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|error| format!("Could not start FastAPI child: {error}"))?;
        let api_pid = api_child.id();
        let manifest_path = app_data.join("runtime.json");
        guard.api = Some(api_child);
        guard.manifest = Some(manifest_path.clone());
        drop(guard);

        let api_manifest = match wait_for_api(&self.0, &manifest_path, api_pid) {
            Ok(manifest) => manifest,
            Err(error) => {
                self.stop();
                return Err(error);
            }
        };

        #[cfg(debug_assertions)]
        {
            let node = std::env::var("NODE").unwrap_or_else(|_| "node".to_string());
            let web_script = repo_root
                .join("apps")
                .join("web")
                .join("node_modules")
                .join("next")
                .join("dist")
                .join("bin")
                .join("next");
            let web_child = Command::new(node)
                .arg(web_script)
                .args(["dev", "--hostname", "127.0.0.1", "--port", "3000"])
                .current_dir(repo_root.join("apps").join("web"))
                .env("NEXT_PUBLIC_API_BASE_URL", &api_manifest.base_url)
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .map_err(|error| format!("Could not start Next.js development server: {error}"))?;
            let web_pid = web_child.id();
            let mut guard = self.0.lock().map_err(|_| "process lock poisoned")?;
            guard.web = Some(web_child);
            drop(guard);
            if let Err(error) = wait_for_web(&self.0, web_pid) {
                self.stop();
                return Err(error);
            }
        }

        Ok(api_manifest)
    }

    fn stop(&self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.web.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
            if let Some(mut child) = guard.api.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
            if let Some(manifest) = guard.manifest.take() {
                let _ = fs::remove_file(manifest);
            }
        }
    }
}

fn proof_local_app_data() -> PathBuf {
    let requested = std::env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|| std::env::temp_dir().join("SAPSOS-tauri-proof"));
    if fs::create_dir_all(requested.join("SAPSOS")).is_ok() {
        return requested;
    }
    let fallback = std::env::temp_dir().join("SAPSOS-tauri-proof");
    fs::create_dir_all(fallback.join("SAPSOS")).expect("could not create proof temp data");
    fallback
}

fn wait_for_api(
    processes: &Mutex<Processes>,
    manifest_path: &Path,
    child_pid: u32,
) -> Result<RuntimeManifest, String> {
    let deadline = Instant::now() + Duration::from_secs(30);
    while Instant::now() < deadline {
        if let Ok(mut guard) = processes.lock() {
            if let Some(child) = guard.api.as_mut() {
                if let Some(status) = child
                    .try_wait()
                    .map_err(|error| format!("Could not inspect FastAPI child: {error}"))?
                {
                    return Err(format!("FastAPI child exited before readiness: {status}"));
                }
            }
        }
        if let Ok(contents) = fs::read_to_string(manifest_path) {
            if let Ok(manifest) = serde_json::from_str::<RuntimeManifest>(&contents) {
                if manifest.pid == child_pid
                    && manifest.status == "ready"
                    && http_probe(manifest.port, "/ready")
                {
                    return Ok(manifest);
                }
            }
        }
        thread::sleep(Duration::from_millis(100));
    }
    Err("FastAPI child did not become ready within 30 seconds".to_string())
}

#[cfg(debug_assertions)]
fn wait_for_web(processes: &Mutex<Processes>, web_pid: u32) -> Result<(), String> {
    let deadline = Instant::now() + Duration::from_secs(30);
    while Instant::now() < deadline {
        if let Ok(mut guard) = processes.lock() {
            if let Some(child) = guard.web.as_mut() {
                if let Some(status) = child
                    .try_wait()
                    .map_err(|error| format!("Could not inspect Next.js child: {error}"))?
                {
                    return Err(format!("Next.js child exited before readiness: {status}"));
                }
            }
        }
        if http_probe(3000, "/") {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(100));
    }
    Err(format!(
        "Next.js child {web_pid} did not become ready within 30 seconds"
    ))
}

fn http_probe(port: u16, path: &str) -> bool {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(500)) else {
        return false;
    };
    if stream
        .write_all(
            format!("GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
                .as_bytes(),
        )
        .is_err()
    {
        return false;
    }
    let mut response = [0_u8; 64];
    let Ok(bytes_read) = stream.read(&mut response) else {
        return false;
    };
    String::from_utf8_lossy(&response[..bytes_read]).starts_with("HTTP/1.1 200")
}

fn main() {
    let context = tauri::generate_context!();
    tauri::Builder::default()
        .manage(DesktopProcesses::default())
        .setup(|app| {
            let api_manifest = app
                .state::<DesktopProcesses>()
                .start()
                .map_err(std::io::Error::other)?;

            #[cfg(not(debug_assertions))]
            {
                let resource_dir = app
                    .path()
                    .resource_dir()
                    .map_err(std::io::Error::other)?;
                if !resource_dir.join("index.html").is_file() {
                    return Err(Box::new(std::io::Error::other(format!(
                        "Packaged Web UI artifact is missing index.html under {}. Build it with scripts/windows/Build-Web-UI.ps1.",
                        resource_dir.display()
                    ))));
                }
            }

            let web_url = if cfg!(debug_assertions) {
                WebviewUrl::External(
                    "http://127.0.0.1:3000"
                        .parse()
                        .map_err(std::io::Error::other)?,
                )
            } else {
                WebviewUrl::App(
                    format!("index.html?api_base_url={}", api_manifest.base_url).into(),
                )
            };
            WebviewWindowBuilder::new(app, "main", web_url)
                .title("SAPSOS Local Desktop")
                .inner_size(1280.0, 860.0)
                .resizable(true)
                .build()
                .map_err(std::io::Error::other)?;
            Ok(())
        })
        .build(context)
        .expect("failed to build Tauri application")
        .run(|app_handle, event| {
            if let RunEvent::Exit = event {
                app_handle.state::<DesktopProcesses>().stop();
            }
        });
}
