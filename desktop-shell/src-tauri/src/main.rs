#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Output, Stdio};
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

#[derive(Debug, Clone, Deserialize)]
struct MigrationContract {
    contract_version: u32,
    command: String,
    database_identity: Option<String>,
    current_schema_version: Option<u32>,
    supported_schema_version: u32,
    schema_status: String,
    migration_required: bool,
    migration_plan: Vec<String>,
    safety_backup_required: bool,
    blocking_reason: Option<String>,
    interrupted_attempt: Option<serde_json::Value>,
    journal_attempt_id: Option<String>,
    attempt_id: Option<String>,
    safety_backup_reference: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct MigrationMarker {
    marker_version: u32,
    attempt_id: String,
    status: String,
    database_identity: String,
    safety_backup_reference: Option<String>,
}

struct StartupLock {
    path: PathBuf,
}

impl StartupLock {
    fn acquire(app_data: &Path) -> Result<Self, String> {
        let path = app_data.join("startup.lock");
        fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)
            .map_err(|_| "Another SAPSOS desktop startup is already in progress.".to_string())?;
        Ok(Self { path })
    }
}

impl Drop for StartupLock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
    }
}

#[derive(Debug, Deserialize)]
struct PendingRestoreMarker {
    marker_version: u32,
    restore_request_id: String,
    backup_id: String,
    staged_database: String,
    expected_sha256: String,
    expected_size: u64,
    expected_schema_version: u32,
    status: String,
}

#[derive(Debug)]
struct RestoreApplication {
    safety_dir: PathBuf,
    marker_path: PathBuf,
    staged_path: PathBuf,
    sidecars: Vec<(PathBuf, PathBuf)>,
    backup_id: String,
}

#[derive(Debug, Serialize)]
struct RestoreStatusFile<'a> {
    status: &'a str,
    backup_id: &'a str,
    message: &'a str,
}

#[derive(Default)]
struct Processes {
    api: Option<Child>,
    web: Option<Child>,
    manifest: Option<PathBuf>,
    cleanup_executable: Option<PathBuf>,
}

#[derive(Default)]
struct DesktopProcesses(Mutex<Processes>);

struct MigrationApplication {
    app_data: PathBuf,
    database: PathBuf,
    marker_path: PathBuf,
    marker: MigrationMarker,
}

fn migration_database_identity(database: &Path) -> String {
    format!(
        "{:x}",
        Sha256::digest(database.to_string_lossy().as_bytes())
    )
}

fn write_migration_marker(path: &Path, marker: &MigrationMarker) -> Result<(), String> {
    let temporary = path.with_extension(format!("{}.tmp", std::process::id()));
    let bytes = serde_json::to_vec(marker)
        .map_err(|error| format!("Could not encode migration marker: {error}"))?;
    fs::write(&temporary, bytes)
        .map_err(|error| format!("Could not write migration marker: {error}"))?;
    fs::rename(&temporary, path)
        .map_err(|error| format!("Could not publish migration marker: {error}"))
}

fn contained_app_path(root: &Path, relative: &str) -> Result<PathBuf, String> {
    let candidate = root.join(relative).components().collect::<PathBuf>();
    if Path::new(relative).is_absolute()
        || Path::new(relative).components().any(|component| {
            matches!(
                component,
                std::path::Component::ParentDir
                    | std::path::Component::RootDir
                    | std::path::Component::Prefix(_)
            )
        })
    {
        return Err("Migration contract contains an unsafe path".to_string());
    }
    let resolved = candidate.canonicalize().unwrap_or(candidate);
    resolved
        .strip_prefix(root)
        .map_err(|_| "Migration contract path escapes app data".to_string())?;
    Ok(resolved)
}

fn run_migration_command(
    executable: &Path,
    arguments: &[String],
    working_directory: &Path,
    app_data: &Path,
    database: &Path,
    command: &str,
) -> Result<MigrationContract, String> {
    let database_url = format!(
        "sqlite+pysqlite:///{}",
        database.to_string_lossy().replace('\\', "/")
    );
    let output: Output = Command::new(executable)
        .args(arguments)
        .arg(command)
        .current_dir(working_directory)
        .env("LOCALAPPDATA", app_data.parent().unwrap_or(app_data))
        .env("DATABASE_URL", database_url)
        .env("PRODUCT_MODE", "LOCAL_DESKTOP")
        .env("AUTH_MODE", "local")
        .env("ENVIRONMENT", "test")
        .env("API_HOST", "127.0.0.1")
        .output()
        .map_err(|error| format!("Could not start migration command: {error}"))?;
    let parsed: MigrationContract = serde_json::from_slice(&output.stdout)
        .map_err(|_| "Migration command returned malformed JSON.".to_string())?;
    if parsed.contract_version != 1 || parsed.command != command {
        return Err("Migration command contract is incompatible.".to_string());
    }
    if parsed.supported_schema_version == 0
        || parsed
            .current_schema_version
            .is_some_and(|version| version > parsed.supported_schema_version)
        || (parsed.migration_required && parsed.migration_plan.is_empty())
        || (parsed.schema_status == "UPGRADE_REQUIRED" && !parsed.safety_backup_required)
    {
        return Err("Migration command returned an inconsistent result.".to_string());
    }
    Ok(parsed)
}

fn rollback_migration(application: &MigrationApplication) -> Result<(), String> {
    let Some(reference) = application.marker.safety_backup_reference.as_deref() else {
        return Err("No safety backup is bound to this migration attempt.".to_string());
    };
    let backup = contained_app_path(&application.app_data, reference)?;
    if !backup.is_file() {
        return Err("The migration safety backup is missing.".to_string());
    }
    let evidence = application
        .app_data
        .join("migration-safety")
        .join(&application.marker.attempt_id)
        .join("failed-database.sqlite");
    if application.database.is_file() {
        fs::rename(&application.database, &evidence)
            .map_err(|error| format!("Could not preserve failed database evidence: {error}"))?;
    }
    for sidecar in sqlite_sidecars(&application.database) {
        if sidecar.is_file() {
            let evidence_sidecar =
                evidence.with_file_name(sidecar.file_name().ok_or("Invalid SQLite sidecar name")?);
            fs::rename(sidecar, evidence_sidecar)
                .map_err(|error| format!("Could not preserve failed SQLite sidecar: {error}"))?;
        }
    }
    let temporary = application.database.with_extension("rollback.tmp");
    fs::copy(&backup, &temporary)
        .map_err(|error| format!("Could not stage migration rollback: {error}"))?;
    if let Err(error) = fs::rename(&temporary, &application.database) {
        let _ = fs::remove_file(&temporary);
        return Err(format!("Could not install migration rollback: {error}"));
    }
    let marker = MigrationMarker {
        status: "ROLLED_BACK".to_string(),
        ..application.marker.clone()
    };
    write_migration_marker(&application.marker_path, &marker)?;
    Ok(())
}

fn prepare_migration(
    api_executable: &Path,
    api_arguments: &[String],
    api_working_directory: &Path,
    app_data: &Path,
    database: &Path,
) -> Result<Option<MigrationApplication>, String> {
    let marker_path = app_data.join("migration-attempt.json");
    if marker_path.is_file() {
        let marker: MigrationMarker = serde_json::from_slice(
            &fs::read(&marker_path)
                .map_err(|error| format!("Could not read migration marker: {error}"))?,
        )
        .map_err(|_| "Migration marker is malformed; startup is blocked.".to_string())?;
        if marker.marker_version != 1
            || marker.database_identity != migration_database_identity(database)
        {
            return Err(
                "Migration marker is unsupported or belongs to another database.".to_string(),
            );
        }
        if marker.status == "ROLLED_BACK" {
            return Err(
                "The previous migration was rolled back; startup is safely stopped.".to_string(),
            );
        }
        let application = MigrationApplication {
            app_data: app_data.to_path_buf(),
            database: database.to_path_buf(),
            marker_path: marker_path.clone(),
            marker,
        };
        rollback_migration(&application)?;
        return Err(
            "An interrupted migration was rolled back; startup is safely stopped.".to_string(),
        );
    }
    let preflight = run_migration_command(
        api_executable,
        api_arguments,
        api_working_directory,
        app_data,
        database,
        "preflight",
    )?;
    if preflight.schema_status == "CURRENT" {
        return Ok(None);
    }
    if preflight.schema_status != "UPGRADE_REQUIRED" || !preflight.migration_required {
        return Err(preflight
            .blocking_reason
            .unwrap_or_else(|| "Local database cannot be safely started.".to_string()));
    }
    if preflight.interrupted_attempt.is_some() {
        return Err("An interrupted local migration requires recovery before startup.".to_string());
    }
    let executed = run_migration_command(
        api_executable,
        api_arguments,
        api_working_directory,
        app_data,
        database,
        "execute",
    )?;
    if executed.schema_status != "CURRENT" {
        if let (Some(attempt_id), Some(database_identity), Some(reference)) = (
            executed
                .attempt_id
                .clone()
                .or(executed.journal_attempt_id.clone()),
            executed.database_identity.clone(),
            executed.safety_backup_reference.clone(),
        ) {
            let marker = MigrationMarker {
                marker_version: 1,
                attempt_id,
                status: "MIGRATION_FAILED".to_string(),
                database_identity,
                safety_backup_reference: Some(reference),
            };
            write_migration_marker(&marker_path, &marker)?;
            let application = MigrationApplication {
                app_data: app_data.to_path_buf(),
                database: database.to_path_buf(),
                marker_path: marker_path.clone(),
                marker,
            };
            rollback_migration(&application)?;
        }
        return Err(executed
            .blocking_reason
            .unwrap_or_else(|| "Local migration failed; startup is safely stopped.".to_string()));
    }
    if executed.safety_backup_reference.is_none() {
        return Err("Local migration did not complete with a validated safety backup.".to_string());
    }
    let attempt_id = executed
        .attempt_id
        .or(executed.journal_attempt_id)
        .ok_or("Migration attempt ID is missing")?;
    let database_identity = executed
        .database_identity
        .ok_or("Migration database identity is missing")?;
    if database_identity != migration_database_identity(database) {
        return Err("Migration used an unexpected database.".to_string());
    }
    let marker = MigrationMarker {
        marker_version: 1,
        attempt_id,
        status: "MIGRATED_BEFORE_READINESS".to_string(),
        database_identity,
        safety_backup_reference: executed.safety_backup_reference,
    };
    write_migration_marker(&marker_path, &marker)?;
    Ok(Some(MigrationApplication {
        app_data: app_data.to_path_buf(),
        database: database.to_path_buf(),
        marker_path,
        marker,
    }))
}

impl DesktopProcesses {
    fn start(&self, packaged_resource_dir: Option<&Path>) -> Result<RuntimeManifest, String> {
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
        let local_app_data = local_app_data_root();
        let app_data = local_app_data.join("SAPSOS");
        fs::create_dir_all(&app_data)
            .map_err(|error| format!("Could not create app-data directory: {error}"))?;
        let _startup_lock = StartupLock::acquire(&app_data)?;
        let database_path = app_data.join("sapsos.db");
        let database_url = format!(
            "sqlite+pysqlite:///{}",
            database_path.to_string_lossy().replace('\\', "/")
        );
        let packaged_api = std::env::var_os("SAPSOS_API_EXECUTABLE")
            .map(PathBuf::from)
            .or_else(|| {
                packaged_resource_dir.map(|root| root.join("runtime/sapsos-api/sapsos-api.exe"))
            });
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
        } else if cfg!(debug_assertions) {
            (
                PathBuf::from(std::env::var("PYTHON").unwrap_or_else(|_| "python".to_string())),
                vec!["-m".to_string(), "app.run".to_string()],
                api_directory.clone(),
            )
        } else {
            return Err("Packaged FastAPI artifact was not configured. Build the Windows package with scripts/windows/Build-Windows-Installer.ps1.".to_string());
        };
        let restore = apply_pending_restore(&app_data, &database_path)?;
        let migration = match prepare_migration(
            &api_executable,
            &api_arguments,
            &api_working_directory,
            &app_data,
            &database_path,
        ) {
            Ok(application) => application,
            Err(error) => {
                if let Some(application) = restore {
                    let _ = rollback_restore(&application, &database_path);
                }
                return Err(error);
            }
        };
        let api_child = Command::new(&api_executable)
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
        let cleanup_executable = if packaged_resource_dir.is_some() {
            Some(api_executable.clone())
        } else {
            None
        };
        guard.api = Some(api_child);
        guard.manifest = Some(manifest_path.clone());
        guard.cleanup_executable = cleanup_executable;
        drop(guard);

        let api_manifest = match wait_for_api(&self.0, &manifest_path, api_pid) {
            Ok(manifest) => {
                if let Some(application) = restore {
                    finalize_restore(&application)?;
                }
                if let Some(application) = &migration {
                    let _ = fs::remove_file(&application.marker_path);
                }
                manifest
            }
            Err(error) => {
                self.stop();
                if let Some(application) = &migration {
                    rollback_migration(application)?;
                }
                if let Some(application) = restore {
                    rollback_restore(&application, &database_path)?;
                }
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
                if let Some(application) = &migration {
                    rollback_migration(application)?;
                }
                return Err(error);
            }
        }

        Ok(api_manifest)
    }

    fn stop(&self) {
        let cleanup_executable = if let Ok(mut guard) = self.0.lock() {
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
            guard.cleanup_executable.take()
        } else {
            None
        };
        let Some(executable) = cleanup_executable else {
            return;
        };
        let plan = std::env::temp_dir()
            .join("SAPSOS-local-data-removal")
            .join("pending-plan.json");
        if !plan.is_file() || !executable.is_file() {
            return;
        }
        let Some(helper_parent) = executable.parent() else {
            return;
        };
        let mut helper = match Command::new(&executable)
            .arg("local-data-remove")
            .current_dir(helper_parent)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
        {
            Ok(process) => process,
            Err(_) => return,
        };
        let deadline = Instant::now() + Duration::from_secs(30);
        while Instant::now() < deadline {
            match helper.try_wait() {
                Ok(Some(_)) => return,
                Ok(None) => thread::sleep(Duration::from_millis(100)),
                Err(_) => return,
            }
        }
        let _ = helper.kill();
        let _ = helper.wait();
    }
}

fn restore_status_path(app_data: &Path) -> PathBuf {
    app_data.join("restore-status.json")
}

fn write_restore_status(
    app_data: &Path,
    status: &str,
    backup_id: &str,
    message: &str,
) -> Result<(), String> {
    let path = restore_status_path(app_data);
    let temporary = path.with_extension(format!("{}.tmp", std::process::id()));
    let contents = serde_json::to_vec(&RestoreStatusFile {
        status,
        backup_id,
        message,
    })
    .map_err(|error| format!("Could not serialize restore status: {error}"))?;
    fs::write(&temporary, contents)
        .map_err(|error| format!("Could not write restore status: {error}"))?;
    fs::rename(temporary, path)
        .map_err(|error| format!("Could not publish restore status: {error}"))
}

fn contained_restore_path(root: &Path, relative: &str) -> Result<PathBuf, String> {
    let relative_path = Path::new(relative);
    if relative_path.is_absolute()
        || relative_path.components().any(|component| {
            matches!(
                component,
                std::path::Component::ParentDir
                    | std::path::Component::RootDir
                    | std::path::Component::Prefix(_)
            )
        })
    {
        return Err("Restore marker contains an unsafe path".to_string());
    }
    Ok(root.join(relative_path))
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let mut file = fs::File::open(path)
        .map_err(|error| format!("Could not open restore candidate: {error}"))?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 1024 * 1024];
    loop {
        let bytes = file
            .read(&mut buffer)
            .map_err(|error| format!("Could not hash restore candidate: {error}"))?;
        if bytes == 0 {
            break;
        }
        digest.update(&buffer[..bytes]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn sqlite_sidecars(database_path: &Path) -> Vec<PathBuf> {
    let file_name = database_path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("database");
    ["-wal", "-shm", "-journal"]
        .iter()
        .map(|suffix| database_path.with_file_name(format!("{file_name}{suffix}")))
        .collect()
}

fn apply_pending_restore(
    app_data: &Path,
    database_path: &Path,
) -> Result<Option<RestoreApplication>, String> {
    let marker_path = app_data.join("pending-restore.json");
    if !marker_path.is_file() {
        return Ok(None);
    }
    let quarantine_dir = app_data.join("restore-safety");
    fs::create_dir_all(&quarantine_dir)
        .map_err(|error| format!("Could not create restore safety copy: {error}"))?;
    let mut quarantined_marker = quarantine_dir.join("invalid-pending-restore.json");
    let mut suffix = 1_u32;
    while quarantined_marker.exists() {
        quarantined_marker = quarantine_dir.join(format!("invalid-pending-restore-{suffix}.json"));
        suffix += 1;
    }
    fs::rename(&marker_path, &quarantined_marker)
        .map_err(|error| format!("Could not consume restore marker: {error}"))?;
    let marker: PendingRestoreMarker = serde_json::from_slice(
        &fs::read(&quarantined_marker)
            .map_err(|error| format!("Could not read restore marker: {error}"))?,
    )
    .map_err(|error| format!("Invalid restore marker; it was quarantined: {error}"))?;
    if marker.marker_version != 1
        || marker.status != "pending"
        || marker.expected_schema_version != 1
    {
        return Err("Restore marker is unsupported or already consumed".to_string());
    }
    let staged_path = contained_restore_path(app_data, &marker.staged_database)?;
    if !staged_path.is_file()
        || fs::metadata(&staged_path)
            .map_err(|error| error.to_string())?
            .len()
            != marker.expected_size
        || sha256_file(&staged_path)? != marker.expected_sha256
    {
        return Err("Restore candidate checksum or size verification failed".to_string());
    }
    let mut header = [0_u8; 16];
    fs::File::open(&staged_path)
        .and_then(|mut file| file.read_exact(&mut header))
        .map_err(|error| format!("Could not read restored SQLite header: {error}"))?;
    if &header != b"SQLite format 3\0" {
        return Err("Restore candidate is not a SQLite database".to_string());
    }
    let safety_dir = app_data
        .join("restore-safety")
        .join(&marker.restore_request_id);
    fs::create_dir_all(&safety_dir)
        .map_err(|error| format!("Could not create restore safety copy: {error}"))?;
    let consumed_marker = safety_dir.join("pending-restore.json");
    fs::rename(&quarantined_marker, &consumed_marker)
        .map_err(|error| format!("Could not consume restore marker: {error}"))?;
    write_restore_status(
        app_data,
        "applying",
        &marker.backup_id,
        "Restore is being applied before API startup.",
    )?;
    let mut sidecars = Vec::new();
    for sidecar in sqlite_sidecars(database_path) {
        if sidecar.is_file() {
            let destination = safety_dir.join(sidecar.file_name().ok_or("Invalid sidecar name")?);
            if let Err(error) = fs::rename(&sidecar, &destination) {
                for (original, preserved) in sidecars.iter().rev() {
                    let _ = fs::rename(preserved, original);
                }
                return Err(format!("Could not preserve SQLite sidecar: {error}"));
            }
            sidecars.push((sidecar, destination));
        }
    }
    let safety_database =
        safety_dir.join(database_path.file_name().ok_or("Invalid database name")?);
    if database_path.is_file() {
        if let Err(error) = fs::rename(database_path, &safety_database) {
            for (original, preserved) in sidecars.iter().rev() {
                let _ = fs::rename(preserved, original);
            }
            return Err(format!("Could not preserve current database: {error}"));
        }
    }
    if let Err(error) = fs::rename(&staged_path, database_path) {
        if safety_database.is_file() {
            let _ = fs::rename(&safety_database, database_path);
        }
        for (original, preserved) in sidecars.iter().rev() {
            let _ = fs::rename(preserved, original);
        }
        return Err(format!("Could not install staged database: {error}"));
    }
    Ok(Some(RestoreApplication {
        safety_dir,
        marker_path,
        staged_path,
        sidecars,
        backup_id: marker.backup_id,
    }))
}

fn finalize_restore(application: &RestoreApplication) -> Result<(), String> {
    let _ = fs::remove_file(&application.marker_path);
    let _ = fs::remove_file(&application.staged_path);
    write_restore_status(
        application
            .marker_path
            .parent()
            .ok_or("Invalid restore marker path")?,
        "succeeded",
        &application.backup_id,
        "Restore completed successfully.",
    )
}

fn rollback_restore(application: &RestoreApplication, database_path: &Path) -> Result<(), String> {
    let quarantine = application.safety_dir.join("failed-restored.sqlite");
    if database_path.is_file() {
        fs::rename(database_path, quarantine)
            .map_err(|error| format!("Could not quarantine failed restored database: {error}"))?;
    }
    let original = application
        .safety_dir
        .join(database_path.file_name().ok_or("Invalid database name")?);
    if original.is_file() {
        fs::rename(original, database_path)
            .map_err(|error| format!("Could not roll back database: {error}"))?;
    }
    for (active, preserved) in &application.sidecars {
        if preserved.is_file() {
            fs::rename(preserved, active)
                .map_err(|error| format!("Could not roll back SQLite sidecar: {error}"))?;
        }
    }
    let _ = fs::remove_file(&application.marker_path);
    write_restore_status(
        application
            .marker_path
            .parent()
            .ok_or("Invalid restore marker path")?,
        "rolled_back",
        &application.backup_id,
        "Restore startup failed; original data was restored.",
    )
}

fn local_app_data_root() -> PathBuf {
    let requested = std::env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|| std::env::temp_dir().join("SAPSOS-local-desktop"));
    if fs::create_dir_all(requested.join("SAPSOS")).is_ok() {
        return requested;
    }
    let fallback = std::env::temp_dir().join("SAPSOS-local-desktop");
    fs::create_dir_all(fallback.join("SAPSOS")).expect("could not create local desktop temp data");
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn test_root(name: &str) -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock before epoch")
            .as_nanos();
        let root = std::env::temp_dir().join(format!("sapsos-restore-{name}-{suffix}"));
        fs::create_dir_all(&root).expect("create test root");
        root
    }

    fn marker(root: &Path, staged: &Path, request_id: &str) {
        let relative = staged.strip_prefix(root).expect("staged path under root");
        let marker = serde_json::json!({
            "marker_version": 1,
            "restore_request_id": request_id,
            "backup_id": "backup-test",
            "staged_database": relative.to_string_lossy().replace('\\', "/"),
            "expected_sha256": sha256_file(staged).expect("hash staged"),
            "expected_size": fs::metadata(staged).expect("staged metadata").len(),
            "expected_schema_version": 1,
            "status": "pending"
        });
        fs::write(root.join("pending-restore.json"), marker.to_string()).expect("write marker");
    }

    #[test]
    fn rejects_restore_path_escape() {
        let root = PathBuf::from(r"C:\safe\app");
        assert!(contained_restore_path(&root, "../outside.sqlite").is_err());
        assert!(contained_restore_path(&root, r"C:\outside.sqlite").is_err());
    }

    #[test]
    fn applies_restore_before_startup_and_prevents_replay() {
        let root = test_root("apply");
        let database = root.join("custom.sqlite");
        let staged = root.join("restore-staging").join("candidate.sqlite");
        fs::create_dir_all(staged.parent().expect("staging parent")).expect("create staging");
        fs::write(&database, b"old").expect("write old");
        fs::write(&staged, b"SQLite format 3\0restored").expect("write staged");
        marker(&root, &staged, "request-1");
        let applied = apply_pending_restore(&root, &database)
            .expect("apply")
            .expect("context");
        assert!(database.is_file());
        assert_eq!(
            fs::read(&database).expect("read active"),
            b"SQLite format 3\0restored"
        );
        finalize_restore(&applied).expect("finalize");
        assert!(!root.join("pending-restore.json").exists());
        assert!(apply_pending_restore(&root, &database)
            .expect("replay check")
            .is_none());
        fs::remove_dir_all(root).expect("remove test root");
    }

    #[test]
    fn rollback_preserves_database_and_sidecars() {
        let root = test_root("rollback");
        let database = root.join("custom.sqlite");
        let sidecar = root.join("custom.sqlite-wal");
        let staged = root.join("restore-staging").join("candidate.sqlite");
        fs::create_dir_all(staged.parent().expect("staging parent")).expect("create staging");
        fs::write(&database, b"old").expect("write old");
        fs::write(&sidecar, b"matching-old-wal").expect("write wal");
        fs::write(&staged, b"SQLite format 3\0restored").expect("write staged");
        marker(&root, &staged, "request-2");
        let applied = apply_pending_restore(&root, &database)
            .expect("apply")
            .expect("context");
        rollback_restore(&applied, &database).expect("rollback");
        assert_eq!(fs::read(&database).expect("read rollback"), b"old");
        assert_eq!(
            fs::read(&sidecar).expect("read sidecar"),
            b"matching-old-wal"
        );
        assert!(!root.join("pending-restore.json").exists());
        fs::remove_dir_all(root).expect("remove test root");
    }

    #[test]
    fn quarantines_corrupt_restore_candidate_without_startup_loop() {
        let root = test_root("corrupt");
        let database = root.join("custom.sqlite");
        let staged = root.join("restore-staging").join("candidate.sqlite");
        fs::create_dir_all(staged.parent().expect("staging parent")).expect("create staging");
        fs::write(&database, b"old").expect("write old");
        fs::write(&staged, b"corrupt").expect("write staged");
        marker(&root, &staged, "request-corrupt");
        assert!(apply_pending_restore(&root, &database).is_err());
        assert!(!root.join("pending-restore.json").exists());
        assert!(root
            .join("restore-safety")
            .join("invalid-pending-restore.json")
            .is_file());
        assert!(apply_pending_restore(&root, &database)
            .expect("relaunch check")
            .is_none());
        fs::remove_dir_all(root).expect("remove test root");
    }
}

fn main() {
    let context = tauri::generate_context!();
    tauri::Builder::default()
        .manage(DesktopProcesses::default())
        .setup(|app| {
            let packaged_resource_dir: Option<PathBuf> = {
                #[cfg(not(debug_assertions))]
                {
                    Some(app.path().resource_dir().map_err(std::io::Error::other)?)
                }
                #[cfg(debug_assertions)]
                {
                    None
                }
            };
            let api_manifest = app
                .state::<DesktopProcesses>()
                .start(packaged_resource_dir.as_deref())
                .map_err(std::io::Error::other)?;

            #[cfg(not(debug_assertions))]
            {
                let resource_dir = packaged_resource_dir
                    .as_deref()
                    .expect("release resource directory is initialized");
                if !resource_dir.join("runtime/sapsos-api/sapsos-api.exe").is_file()
                    && std::env::var_os("SAPSOS_API_EXECUTABLE").is_none()
                {
                    return Err(Box::new(std::io::Error::other(format!(
                        "Packaged FastAPI artifact is missing under {}. Build it with scripts/windows/Build-FastAPI-Runtime.ps1.",
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
