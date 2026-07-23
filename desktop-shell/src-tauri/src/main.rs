#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
#[cfg(not(windows))]
use std::fs::File;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Output, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use uuid::Uuid;

#[cfg(windows)]
use std::os::windows::ffi::OsStrExt;
#[cfg(windows)]
use windows_sys::Win32::Foundation::{CloseHandle, GetLastError, ERROR_ALREADY_EXISTS, HANDLE};
#[cfg(windows)]
use windows_sys::Win32::System::Threading::{CreateMutexW, ReleaseMutex};

#[derive(Debug, Deserialize)]
struct RuntimeManifest {
    instance_id: Uuid,
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

#[derive(Debug, Serialize)]
struct StartupLockDiagnostic {
    diagnostic_version: u32,
    timestamp_unix_seconds: u64,
    app_version: &'static str,
    source_head_sha: Option<&'static str>,
    build_identity: Option<&'static str>,
    lock_path: String,
    lock_exists: bool,
    acquisition_result: &'static str,
    live_owner_detected: Option<bool>,
    trusted_owner_pid: Option<u32>,
    stale_recovery_attempted: bool,
    recovery_result: &'static str,
    final_startup_outcome: &'static str,
}

#[derive(Debug)]
enum StartupLockError {
    Contended(PathBuf),
    Failed(PathBuf, String),
}

impl std::fmt::Display for StartupLockError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Contended(path) => write!(
                formatter,
                "STARTUP_LOCK_CONTENDED: Another SAPSOS desktop startup is already in progress at {}.",
                path.display()
            ),
            Self::Failed(path, error) => write!(
                formatter,
                "Could not acquire SAPSOS desktop startup lock at {}: {error}",
                path.display()
            ),
        }
    }
}

#[derive(Debug)]
struct StartupLock {
    path: PathBuf,
    #[cfg(windows)]
    mutex: HANDLE,
    #[cfg(not(windows))]
    file: File,
}

// The mutex handle is owned and released only while protected by the
// DesktopProcesses mutex; transferring that owner between Tauri state
// threads does not duplicate or concurrently use the handle.
#[cfg(windows)]
unsafe impl Send for StartupLock {}

impl StartupLock {
    fn acquire(app_data: &Path) -> Result<Self, StartupLockError> {
        let path = app_data.join("startup.lock");
        let mutex_name = startup_mutex_name(app_data);

        #[cfg(windows)]
        let mutex = {
            let name: Vec<u16> = std::ffi::OsStr::new(&mutex_name)
                .encode_wide()
                .chain(std::iter::once(0))
                .collect();
            let handle = unsafe { CreateMutexW(std::ptr::null(), 1, name.as_ptr()) };
            if handle.is_null() {
                let error = std::io::Error::last_os_error().to_string();
                write_startup_lock_diagnostic(
                    app_data,
                    "acquisition_failed",
                    None,
                    false,
                    "not_attempted",
                    "rejected",
                );
                return Err(StartupLockError::Failed(path, error));
            }
            if unsafe { GetLastError() } == ERROR_ALREADY_EXISTS {
                unsafe { CloseHandle(handle) };
                write_startup_lock_diagnostic(
                    app_data,
                    "rejected_contended",
                    Some(true),
                    false,
                    "not_attempted",
                    "rejected",
                );
                return Err(StartupLockError::Contended(path));
            }
            handle
        };

        #[cfg(windows)]
        if let Err(error) = fs::write(
            &path,
            format!(
                "{{\"marker_version\":1,\"pid\":{},\"app_version\":\"{}\"}}",
                std::process::id(),
                env!("CARGO_PKG_VERSION")
            ),
        ) {
            unsafe {
                let _ = ReleaseMutex(mutex);
                let _ = CloseHandle(mutex);
            }
            return Err(StartupLockError::Failed(path, error.to_string()));
        }

        #[cfg(not(windows))]
        let file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)
            .map_err(|error| {
                write_startup_lock_diagnostic(
                    app_data,
                    "rejected_contended",
                    Some(true),
                    false,
                    "not_attempted",
                    "rejected",
                );
                StartupLockError::Failed(path.clone(), error.to_string())
            })?;

        let lock = Self {
            path,
            #[cfg(windows)]
            mutex,
            #[cfg(not(windows))]
            file,
        };
        write_startup_lock_diagnostic(
            app_data,
            "acquired",
            Some(false),
            true,
            "not_needed",
            "startup_continues",
        );
        Ok(lock)
    }
}

impl Drop for StartupLock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
        if let Some(app_data) = self.path.parent() {
            write_startup_lock_diagnostic(
                app_data,
                "released",
                Some(false),
                false,
                "released",
                "startup_stopped",
            );
        }
        #[cfg(windows)]
        unsafe {
            let _ = ReleaseMutex(self.mutex);
            let _ = CloseHandle(self.mutex);
        }
    }
}

fn startup_mutex_name(app_data: &Path) -> String {
    let normalized = app_data.to_string_lossy().to_ascii_lowercase();
    let digest = Sha256::digest(normalized.as_bytes());
    format!(
        "Local\\SAPSOS.Desktop.Startup.{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}",
        digest[0], digest[1], digest[2], digest[3], digest[4], digest[5], digest[6], digest[7]
    )
}

fn write_startup_lock_diagnostic(
    app_data: &Path,
    acquisition_result: &'static str,
    live_owner_detected: Option<bool>,
    stale_recovery_attempted: bool,
    recovery_result: &'static str,
    final_startup_outcome: &'static str,
) {
    let diagnostic = StartupLockDiagnostic {
        diagnostic_version: 1,
        timestamp_unix_seconds: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |duration| duration.as_secs()),
        app_version: env!("CARGO_PKG_VERSION"),
        source_head_sha: option_env!("SAPSOS_SOURCE_HEAD_SHA"),
        build_identity: option_env!("SAPSOS_BUILD_IDENTITY"),
        lock_path: app_data.join("startup.lock").display().to_string(),
        lock_exists: app_data.join("startup.lock").exists(),
        acquisition_result,
        live_owner_detected,
        trusted_owner_pid: None,
        stale_recovery_attempted,
        recovery_result,
        final_startup_outcome,
    };
    let path = app_data.join("startup-lock-diagnostics.json");
    if let Ok(contents) = serde_json::to_vec_pretty(&diagnostic) {
        let _ = fs::write(path, contents);
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
    startup_lock: Option<StartupLock>,
    api: Option<Child>,
    api_spawn_root: Option<TrustedProcessIdentity>,
    api_runtime: Option<TrustedRuntimeIdentity>,
    api_expected_instance_id: Option<Uuid>,
    api_launch_started_at: Option<u64>,
    api_expected_executable: Option<PathBuf>,
    web: Option<Child>,
    manifest: Option<PathBuf>,
    cleanup_executable: Option<PathBuf>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct TrustedProcessIdentity {
    pid: u32,
    executable_path: Option<PathBuf>,
    parent_pid: Option<u32>,
    creation_time: Option<u64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RuntimeOwnershipMode {
    SameProcess,
    SpawnDescendant,
    TauriHandoff,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct TrustedRuntimeIdentity {
    process: TrustedProcessIdentity,
    instance_id: Uuid,
    ownership_mode: RuntimeOwnershipMode,
}

const MAX_PROCESS_ANCESTRY_DEPTH: usize = 16;
const LAUNCH_CLOCK_TOLERANCE_100NS: u64 = 2 * 10_000_000;
const API_READINESS_TIMEOUT_SECONDS: u64 = 30;

fn normalized_executable_path(path: &Path) -> Option<PathBuf> {
    fs::canonicalize(path).ok()
}

fn process_identity_is_exact(identity: &TrustedProcessIdentity, expected: &Path) -> bool {
    identity
        .executable_path
        .as_deref()
        .and_then(normalized_executable_path)
        .zip(normalized_executable_path(expected))
        .is_some_and(|(actual, expected)| actual == expected)
}

fn same_process_identity(
    expected: &TrustedProcessIdentity,
    actual: &TrustedProcessIdentity,
) -> bool {
    expected.pid == actual.pid
        && expected.creation_time.is_some()
        && expected.creation_time == actual.creation_time
        && expected
            .executable_path
            .as_deref()
            .and_then(normalized_executable_path)
            == actual
                .executable_path
                .as_deref()
                .and_then(normalized_executable_path)
}

fn creation_time_is_in_launch_window(
    creation_time: Option<u64>,
    launch_started_at: u64,
    readiness_deadline: u64,
) -> bool {
    creation_time.is_some_and(|time| {
        time >= launch_started_at.saturating_sub(LAUNCH_CLOCK_TOLERANCE_100NS)
            && time <= readiness_deadline
    })
}

fn lineage_reaches(
    candidate: &TrustedProcessIdentity,
    target: &TrustedProcessIdentity,
    graph: &[TrustedProcessIdentity],
) -> bool {
    let mut current = candidate;
    let mut visited = vec![current.pid];
    for _ in 0..MAX_PROCESS_ANCESTRY_DEPTH {
        let Some(parent_pid) = current.parent_pid else {
            return false;
        };
        if visited.contains(&parent_pid) {
            return false;
        }
        if parent_pid == target.pid {
            let Some(parent) = graph.iter().find(|item| item.pid == parent_pid) else {
                return false;
            };
            return same_process_identity(target, parent);
        }
        let Some(parent) = graph.iter().find(|item| item.pid == parent_pid) else {
            return false;
        };
        current = parent;
        visited.push(current.pid);
    }
    false
}

fn trusted_runtime_from_graph(
    spawn_root: &TrustedProcessIdentity,
    tauri_identity: &TrustedProcessIdentity,
    candidate_pid: u32,
    expected_executable: &Path,
    expected_instance_id: Uuid,
    observed_instance_id: Uuid,
    launch_started_at: u64,
    readiness_deadline: u64,
    graph: &[TrustedProcessIdentity],
) -> Option<TrustedRuntimeIdentity> {
    if observed_instance_id != expected_instance_id {
        return None;
    }
    let candidate = graph.iter().find(|item| item.pid == candidate_pid)?;
    if !process_identity_is_exact(candidate, expected_executable)
        || !creation_time_is_in_launch_window(
            candidate.creation_time,
            launch_started_at,
            readiness_deadline,
        )
    {
        return None;
    }
    let ownership_mode = if candidate.pid == spawn_root.pid {
        same_process_identity(spawn_root, candidate).then_some(RuntimeOwnershipMode::SameProcess)
    } else if lineage_reaches(candidate, spawn_root, graph) {
        Some(RuntimeOwnershipMode::SpawnDescendant)
    } else if lineage_reaches(candidate, tauri_identity, graph) {
        Some(RuntimeOwnershipMode::TauriHandoff)
    } else {
        None
    }?;
    Some(TrustedRuntimeIdentity {
        process: candidate.clone(),
        instance_id: expected_instance_id,
        ownership_mode,
    })
}

#[cfg(windows)]
mod windows_process {
    use super::{normalized_executable_path, TrustedProcessIdentity};
    use std::collections::HashMap;
    use std::ffi::OsString;
    use std::os::windows::ffi::OsStringExt;
    use std::path::PathBuf;
    use std::thread;
    use std::time::{Duration, Instant};
    use windows_sys::Win32::Foundation::{CloseHandle, FILETIME, HANDLE};
    use windows_sys::Win32::System::Diagnostics::ToolHelp::{
        CreateToolhelp32Snapshot, Process32FirstW, Process32NextW, PROCESSENTRY32W,
        TH32CS_SNAPPROCESS,
    };
    use windows_sys::Win32::System::SystemInformation::GetSystemTimeAsFileTime;
    use windows_sys::Win32::System::Threading::{
        GetProcessTimes, OpenProcess, QueryFullProcessImageNameW, TerminateProcess,
        PROCESS_QUERY_LIMITED_INFORMATION, PROCESS_TERMINATE,
    };

    struct Handle(HANDLE);
    impl Drop for Handle {
        fn drop(&mut self) {
            if !self.0.is_null() {
                unsafe { CloseHandle(self.0) };
            }
        }
    }

    fn process_handle(pid: u32, rights: u32) -> Option<Handle> {
        let handle = unsafe { OpenProcess(rights, 0, pid) };
        (!handle.is_null()).then_some(Handle(handle))
    }

    fn creation_time(handle: HANDLE) -> Option<u64> {
        let mut created = FILETIME {
            dwLowDateTime: 0,
            dwHighDateTime: 0,
        };
        let mut exited = FILETIME {
            dwLowDateTime: 0,
            dwHighDateTime: 0,
        };
        let mut kernel = FILETIME {
            dwLowDateTime: 0,
            dwHighDateTime: 0,
        };
        let mut user = FILETIME {
            dwLowDateTime: 0,
            dwHighDateTime: 0,
        };
        let ok =
            unsafe { GetProcessTimes(handle, &mut created, &mut exited, &mut kernel, &mut user) };
        (ok != 0)
            .then_some((u64::from(created.dwHighDateTime) << 32) | u64::from(created.dwLowDateTime))
    }

    fn executable_path(handle: HANDLE) -> Option<PathBuf> {
        let mut buffer = vec![0_u16; 32768];
        let mut length = buffer.len() as u32;
        let ok = unsafe { QueryFullProcessImageNameW(handle, 0, buffer.as_mut_ptr(), &mut length) };
        if ok == 0 || length == 0 {
            return None;
        }
        normalized_executable_path(&PathBuf::from(OsString::from_wide(
            &buffer[..length as usize],
        )))
    }

    fn parent_pid(pid: u32) -> Option<u32> {
        let snapshot = unsafe { CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0) };
        if snapshot.is_null() {
            return None;
        }
        let snapshot = Handle(snapshot);
        let mut entry = PROCESSENTRY32W {
            dwSize: std::mem::size_of::<PROCESSENTRY32W>() as u32,
            ..unsafe { std::mem::zeroed() }
        };
        let mut found = unsafe { Process32FirstW(snapshot.0, &mut entry) } != 0;
        while found {
            if entry.th32ProcessID == pid {
                return Some(entry.th32ParentProcessID);
            }
            found = unsafe { Process32NextW(snapshot.0, &mut entry) } != 0;
        }
        None
    }

    fn process_parents() -> Option<HashMap<u32, u32>> {
        let snapshot = unsafe { CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0) };
        if snapshot.is_null() {
            return None;
        }
        let snapshot = Handle(snapshot);
        let mut entry = PROCESSENTRY32W {
            dwSize: std::mem::size_of::<PROCESSENTRY32W>() as u32,
            ..unsafe { std::mem::zeroed() }
        };
        let mut parents = HashMap::new();
        let mut found = unsafe { Process32FirstW(snapshot.0, &mut entry) } != 0;
        while found {
            parents.insert(entry.th32ProcessID, entry.th32ParentProcessID);
            found = unsafe { Process32NextW(snapshot.0, &mut entry) } != 0;
        }
        Some(parents)
    }

    fn capture_with_parent(pid: u32, parent_pid: Option<u32>) -> Option<TrustedProcessIdentity> {
        let handle = process_handle(pid, PROCESS_QUERY_LIMITED_INFORMATION)?;
        Some(TrustedProcessIdentity {
            pid,
            executable_path: executable_path(handle.0),
            parent_pid,
            creation_time: creation_time(handle.0),
        })
    }

    pub(super) fn capture(pid: u32) -> Option<TrustedProcessIdentity> {
        capture_with_parent(pid, parent_pid(pid))
    }

    pub(super) fn capture_process_lineage(
        candidate_pid: u32,
        anchors: &[&TrustedProcessIdentity],
    ) -> Option<Vec<TrustedProcessIdentity>> {
        let parents = process_parents()?;
        let mut graph = Vec::new();
        let mut pid = candidate_pid;
        for _ in 0..=super::MAX_PROCESS_ANCESTRY_DEPTH {
            let parent = *parents.get(&pid)?;
            graph.push(capture_with_parent(pid, Some(parent))?);
            if let Some(anchor) = anchors.iter().find(|anchor| anchor.pid == parent) {
                graph.push((*anchor).clone());
                return Some(graph);
            }
            if parent == pid {
                return Some(graph);
            }
            pid = parent;
        }
        Some(graph)
    }

    pub(super) fn now_filetime() -> u64 {
        let mut current = FILETIME {
            dwLowDateTime: 0,
            dwHighDateTime: 0,
        };
        unsafe { GetSystemTimeAsFileTime(&mut current) };
        (u64::from(current.dwHighDateTime) << 32) | u64::from(current.dwLowDateTime)
    }

    pub(super) fn terminate(identity: &TrustedProcessIdentity) -> bool {
        let Some(current) = capture(identity.pid) else {
            return false;
        };
        if !super::same_process_identity(identity, &current) {
            return false;
        }
        let Some(handle) = process_handle(
            identity.pid,
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE,
        ) else {
            return false;
        };
        unsafe { TerminateProcess(handle.0, 1) != 0 }
    }

    pub(super) fn wait_until_gone(identity: &TrustedProcessIdentity, timeout: Duration) -> bool {
        let deadline = Instant::now() + timeout;
        while Instant::now() < deadline {
            match capture(identity.pid) {
                None => return true,
                Some(current) if !super::same_process_identity(identity, &current) => return false,
                Some(_) => thread::sleep(Duration::from_millis(100)),
            }
        }
        capture(identity.pid).is_none()
    }
}

#[cfg(windows)]
fn capture_process_identity(pid: u32) -> Option<TrustedProcessIdentity> {
    windows_process::capture(pid)
}

#[cfg(not(windows))]
fn capture_process_identity(pid: u32) -> Option<TrustedProcessIdentity> {
    Some(TrustedProcessIdentity {
        pid,
        executable_path: None,
        parent_pid: None,
        creation_time: None,
    })
}

#[cfg(windows)]
fn process_launch_time() -> u64 {
    windows_process::now_filetime()
}

#[cfg(not(windows))]
fn process_launch_time() -> u64 {
    0
}

fn trusted_runtime_identity(
    spawn_root: &TrustedProcessIdentity,
    tauri_identity: &TrustedProcessIdentity,
    candidate_pid: u32,
    expected_executable: &Path,
    expected_instance_id: Uuid,
    observed_instance_id: Uuid,
    launch_started_at: u64,
    readiness_deadline: u64,
) -> Option<TrustedRuntimeIdentity> {
    #[cfg(windows)]
    {
        let graph =
            windows_process::capture_process_lineage(candidate_pid, &[spawn_root, tauri_identity])?;
        return trusted_runtime_from_graph(
            spawn_root,
            tauri_identity,
            candidate_pid,
            expected_executable,
            expected_instance_id,
            observed_instance_id,
            launch_started_at,
            readiness_deadline,
            &graph,
        );
    }
    #[cfg(not(windows))]
    {
        (candidate_pid == spawn_root.pid && observed_instance_id == expected_instance_id).then(
            || TrustedRuntimeIdentity {
                process: spawn_root.clone(),
                instance_id: expected_instance_id,
                ownership_mode: RuntimeOwnershipMode::SameProcess,
            },
        )
    }
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

fn runtime_path(working_directory: &Path) -> Option<std::ffi::OsString> {
    let mut paths = vec![working_directory.to_path_buf()];
    if let Some(existing) = std::env::var_os("PATH") {
        paths.extend(std::env::split_paths(&existing));
    }
    std::env::join_paths(paths).ok()
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
        .env("PATH", runtime_path(working_directory).unwrap_or_default())
        .env("LOCALAPPDATA", app_data.parent().unwrap_or(app_data))
        .env("DATABASE_URL", database_url)
        .env("PRODUCT_MODE", "LOCAL_DESKTOP")
        .env("AUTH_MODE", "local")
        .env("ENVIRONMENT", "test")
        .env("API_HOST", "127.0.0.1")
        .output()
        .map_err(|error| format!("Could not start migration command: {error}"))?;
    let parsed: MigrationContract = serde_json::from_slice(&output.stdout).map_err(|_| {
        fn diagnostic(bytes: &[u8]) -> String {
            String::from_utf8_lossy(bytes)
                .chars()
                .take(4096)
                .collect::<String>()
                .replace('\r', "\\r")
                .replace('\n', "\\n")
        }

        format!(
            "Migration command returned malformed JSON (stdout_len={}, stderr_len={}, stdout_prefix={:?}, stderr_prefix={:?}).",
            output.stdout.len(),
            output.stderr.len(),
            diagnostic(&output.stdout),
            diagnostic(&output.stderr),
        )
    })?;
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
        let startup_lock = StartupLock::acquire(&app_data).map_err(|error| error.to_string())?;
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
        let tauri_identity = capture_process_identity(std::process::id())
            .ok_or_else(|| "Could not capture Tauri process identity".to_string())?;
        let expected_runtime_instance_id = Uuid::new_v4();
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
        let launch_started_at = process_launch_time();
        let api_child = Command::new(&api_executable)
            .args(api_arguments)
            .current_dir(&api_working_directory)
            .env(
                "PATH",
                runtime_path(&api_working_directory).unwrap_or_default(),
            )
            .env("LOCALAPPDATA", &local_app_data)
            .env("DATABASE_URL", database_url)
            .env("PRODUCT_MODE", "LOCAL_DESKTOP")
            .env("AUTH_MODE", "local")
            .env("ENVIRONMENT", "test")
            .env("API_HOST", "127.0.0.1")
            .env("API_PORT", "0")
            .env(
                "SAPSOS_RUNTIME_INSTANCE_ID",
                expected_runtime_instance_id.to_string(),
            )
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|error| format!("Could not start FastAPI child: {error}"))?;
        let api_pid = api_child.id();
        let expected_executable =
            normalized_executable_path(&api_executable).unwrap_or_else(|| api_executable.clone());
        let api_spawn_root = capture_process_identity(api_pid)
            .ok_or_else(|| "Could not capture packaged API spawn identity".to_string())?;
        let manifest_path = app_data.join("runtime.json");
        let cleanup_executable = if packaged_resource_dir.is_some() {
            Some(api_executable.clone())
        } else {
            None
        };
        guard.api = Some(api_child);
        guard.api_spawn_root = Some(api_spawn_root.clone());
        guard.api_expected_instance_id = Some(expected_runtime_instance_id);
        guard.api_launch_started_at = Some(launch_started_at);
        guard.api_expected_executable = Some(expected_executable.clone());
        guard.api_runtime = None;
        guard.manifest = Some(manifest_path.clone());
        guard.cleanup_executable = cleanup_executable;
        drop(guard);

        let api_manifest = match wait_for_api(
            &self.0,
            &manifest_path,
            &api_spawn_root,
            &tauri_identity,
            &expected_executable,
            expected_runtime_instance_id,
            launch_started_at,
        ) {
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

        let mut guard = self.0.lock().map_err(|_| "process lock poisoned")?;
        guard.startup_lock = Some(startup_lock);
        drop(guard);
        Ok(api_manifest)
    }

    fn stop(&self) {
        let (cleanup_executable, api_runtime, expected_instance_id, manifest_path, startup_lock) =
            if let Ok(mut guard) = self.0.lock() {
                if let Some(mut child) = guard.web.take() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
                if let Some(mut child) = guard.api.take() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
                let api_runtime = guard.api_runtime.take();
                guard.api_spawn_root.take();
                let expected_instance_id = guard.api_expected_instance_id.take();
                guard.api_launch_started_at.take();
                guard.api_expected_executable.take();
                (
                    guard.cleanup_executable.take(),
                    api_runtime,
                    expected_instance_id,
                    guard.manifest.take(),
                    guard.startup_lock.take(),
                )
            } else {
                (None, None, None, None, None)
            };
        #[cfg(windows)]
        let mut runtime_cleanup_allowed = true;
        #[cfg(windows)]
        if let Some(identity) = api_runtime {
            let _ = windows_process::terminate(&identity.process);
            runtime_cleanup_allowed = windows_process::wait_until_gone(
                &identity.process,
                Duration::from_secs(API_READINESS_TIMEOUT_SECONDS),
            );
        }
        if let (Some(manifest_path), Some(expected_instance_id)) =
            (manifest_path, expected_instance_id)
        {
            let owned = fs::read_to_string(&manifest_path)
                .ok()
                .and_then(|contents| serde_json::from_str::<RuntimeManifest>(&contents).ok())
                .is_some_and(|manifest| manifest.instance_id == expected_instance_id);
            if owned && {
                #[cfg(windows)]
                {
                    runtime_cleanup_allowed
                }
                #[cfg(not(windows))]
                {
                    true
                }
            } {
                let _ = fs::remove_file(manifest_path);
            }
        }
        let Some(executable) = cleanup_executable else {
            drop(startup_lock);
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
        drop(startup_lock);
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
    spawn_root: &TrustedProcessIdentity,
    tauri_identity: &TrustedProcessIdentity,
    expected_executable: &Path,
    expected_instance_id: Uuid,
    launch_started_at: u64,
) -> Result<RuntimeManifest, String> {
    let deadline = Instant::now() + Duration::from_secs(API_READINESS_TIMEOUT_SECONDS);
    let readiness_deadline =
        launch_started_at.saturating_add(API_READINESS_TIMEOUT_SECONDS * 10_000_000);
    let mut provisional_runtime = None;
    while Instant::now() < deadline {
        if let Ok(contents) = fs::read_to_string(manifest_path) {
            if let Ok(manifest) = serde_json::from_str::<RuntimeManifest>(&contents) {
                if manifest.instance_id != expected_instance_id {
                    thread::sleep(Duration::from_millis(100));
                    continue;
                }
                if manifest.status == "ready" {
                    if manifest.port == 0
                        || manifest.base_url != format!("http://127.0.0.1:{}", manifest.port)
                    {
                        thread::sleep(Duration::from_millis(100));
                        continue;
                    }
                    let Some(runtime) = trusted_runtime_identity(
                        spawn_root,
                        tauri_identity,
                        manifest.pid,
                        expected_executable,
                        expected_instance_id,
                        manifest.instance_id,
                        launch_started_at,
                        readiness_deadline,
                    ) else {
                        thread::sleep(Duration::from_millis(100));
                        continue;
                    };
                    provisional_runtime = Some(runtime.clone());
                    if let Ok(mut guard) = processes.lock() {
                        guard.api_runtime = provisional_runtime.clone();
                    }
                    if http_probe(manifest.port, "/ready") {
                        return Ok(manifest);
                    }
                }
            }
        }
        thread::sleep(Duration::from_millis(100));
    }
    let _ = provisional_runtime;
    Err("PACKAGED_API_IDENTITY_MISMATCH: packaged API did not become ready with a trusted process identity within 30 seconds".to_string())
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

fn readiness_probe_request(port: u16, path: &str) -> Vec<u8> {
    format!("GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n")
        .into_bytes()
}

fn http_probe(port: u16, path: &str) -> bool {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(500)) else {
        return false;
    };
    if stream
        .write_all(&readiness_probe_request(port, path))
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

    fn process_fixture(root: &Path) -> (PathBuf, TrustedProcessIdentity) {
        let executable = root.join("sapsos-api.exe");
        fs::write(&executable, b"test").expect("write executable fixture");
        let identity = TrustedProcessIdentity {
            pid: 10,
            executable_path: Some(executable.clone()),
            parent_pid: Some(20),
            creation_time: Some(100_000_000),
        };
        (executable, identity)
    }

    fn tauri_fixture(root: &Path) -> TrustedProcessIdentity {
        let executable = root.join("sapsos-local-desktop.exe");
        fs::write(&executable, b"tauri").expect("write Tauri fixture");
        TrustedProcessIdentity {
            pid: 20,
            executable_path: Some(executable),
            parent_pid: Some(1),
            creation_time: Some(90_000_000),
        }
    }

    fn expected_instance_id() -> Uuid {
        Uuid::from_u128(0x1234_5678_1234_4234_8234_1234_5678_9abc)
    }

    fn trust(
        spawn: &TrustedProcessIdentity,
        tauri: &TrustedProcessIdentity,
        candidate_pid: u32,
        executable: &Path,
        instance_id: Uuid,
        graph: &[TrustedProcessIdentity],
    ) -> Option<TrustedRuntimeIdentity> {
        trust_with_observed_instance(
            spawn,
            tauri,
            candidate_pid,
            executable,
            instance_id,
            instance_id,
            graph,
        )
    }

    fn trust_with_observed_instance(
        spawn: &TrustedProcessIdentity,
        tauri: &TrustedProcessIdentity,
        candidate_pid: u32,
        executable: &Path,
        expected_instance_id: Uuid,
        observed_instance_id: Uuid,
        graph: &[TrustedProcessIdentity],
    ) -> Option<TrustedRuntimeIdentity> {
        trusted_runtime_from_graph(
            spawn,
            tauri,
            candidate_pid,
            executable,
            expected_instance_id,
            observed_instance_id,
            100_000_000,
            200_000_000,
            graph,
        )
    }

    #[test]
    fn trusted_identity_accepts_same_process_with_correct_instance() {
        let root = test_root("identity-root");
        let (executable, spawn) = process_fixture(&root);
        let tauri = tauri_fixture(&root);
        let trusted = trust(
            &spawn,
            &tauri,
            10,
            &executable,
            expected_instance_id(),
            &[spawn.clone()],
        )
        .expect("same process should be trusted");
        assert_eq!(trusted.ownership_mode, RuntimeOwnershipMode::SameProcess);
        fs::remove_dir_all(root).expect("remove test root");
    }

    #[test]
    fn trusted_identity_accepts_spawn_descendant_and_grandchild() {
        let root = test_root("identity-descendants");
        let (executable, spawn) = process_fixture(&root);
        let tauri = tauri_fixture(&root);
        let child = TrustedProcessIdentity {
            pid: 11,
            parent_pid: Some(10),
            creation_time: Some(100_000_001),
            ..spawn.clone()
        };
        let grandchild = TrustedProcessIdentity {
            pid: 12,
            parent_pid: Some(11),
            creation_time: Some(100_000_002),
            ..spawn.clone()
        };
        let graph = vec![grandchild.clone(), child.clone(), spawn.clone()];
        assert_eq!(
            trust(
                &spawn,
                &tauri,
                11,
                &executable,
                expected_instance_id(),
                &graph,
            )
            .expect("descendant should be trusted")
            .ownership_mode,
            RuntimeOwnershipMode::SpawnDescendant
        );
        assert_eq!(
            trust(
                &spawn,
                &tauri,
                12,
                &executable,
                expected_instance_id(),
                &graph,
            )
            .expect("grandchild should be trusted")
            .ownership_mode,
            RuntimeOwnershipMode::SpawnDescendant
        );
        fs::remove_dir_all(root).expect("remove test root");
    }

    #[test]
    fn trusted_identity_accepts_tauri_handoff_child_and_grandchild() {
        let root = test_root("identity-handoff");
        let (executable, spawn) = process_fixture(&root);
        let tauri = tauri_fixture(&root);
        let handoff_child = TrustedProcessIdentity {
            pid: 30,
            parent_pid: Some(20),
            creation_time: Some(100_000_001),
            ..spawn.clone()
        };
        let handoff_grandchild = TrustedProcessIdentity {
            pid: 31,
            parent_pid: Some(30),
            creation_time: Some(100_000_002),
            ..spawn.clone()
        };
        let graph = vec![
            handoff_grandchild.clone(),
            handoff_child.clone(),
            tauri.clone(),
        ];
        assert_eq!(
            trust(
                &spawn,
                &tauri,
                30,
                &executable,
                expected_instance_id(),
                &graph,
            )
            .expect("handoff child should be trusted")
            .ownership_mode,
            RuntimeOwnershipMode::TauriHandoff
        );
        assert_eq!(
            trust(
                &spawn,
                &tauri,
                31,
                &executable,
                expected_instance_id(),
                &graph,
            )
            .expect("handoff grandchild should be trusted")
            .ownership_mode,
            RuntimeOwnershipMode::TauriHandoff
        );
        fs::remove_dir_all(root).expect("remove test root");
    }

    #[test]
    fn trusted_identity_rejects_wrong_instance_and_executable() {
        let root = test_root("identity-rejections");
        let (executable, spawn) = process_fixture(&root);
        let tauri = tauri_fixture(&root);
        let unrelated = TrustedProcessIdentity {
            pid: 12,
            parent_pid: Some(1),
            creation_time: Some(100_000_002),
            ..spawn.clone()
        };
        let other = root.join("other.exe");
        fs::write(&other, b"other").expect("write other fixture");
        let wrong = TrustedProcessIdentity {
            pid: 11,
            parent_pid: Some(10),
            executable_path: Some(other),
            creation_time: Some(100_000_001),
            ..spawn.clone()
        };
        assert!(trust(
            &spawn,
            &tauri,
            12,
            &executable,
            expected_instance_id(),
            &[spawn.clone(), unrelated],
        )
        .is_none());
        assert!(trust(
            &spawn,
            &tauri,
            11,
            &executable,
            expected_instance_id(),
            &[spawn.clone(), wrong],
        )
        .is_none());
        let handoff = TrustedProcessIdentity {
            pid: 30,
            parent_pid: Some(20),
            creation_time: Some(100_000_001),
            ..spawn.clone()
        };
        assert!(trust_with_observed_instance(
            &spawn,
            &tauri,
            30,
            &executable,
            expected_instance_id(),
            Uuid::new_v4(),
            &[handoff, tauri.clone()],
        )
        .is_none());
        fs::remove_dir_all(root).expect("remove test root");
    }

    #[test]
    fn trusted_identity_rejects_prelaunch_process_and_unrelated_ancestry() {
        let root = test_root("identity-race");
        let (executable, spawn) = process_fixture(&root);
        let tauri = tauri_fixture(&root);
        let prelaunch = TrustedProcessIdentity {
            pid: 11,
            parent_pid: Some(20),
            creation_time: Some(0),
            ..spawn.clone()
        };
        let unrelated = TrustedProcessIdentity {
            pid: 12,
            parent_pid: Some(99),
            creation_time: Some(100_000_002),
            ..spawn.clone()
        };
        assert!(trust(
            &spawn,
            &tauri,
            11,
            &executable,
            expected_instance_id(),
            &[prelaunch, tauri.clone()],
        )
        .is_none());
        assert!(trust(
            &spawn,
            &tauri,
            12,
            &executable,
            expected_instance_id(),
            &[unrelated],
        )
        .is_none());
        fs::remove_dir_all(root).expect("remove test root");
    }

    #[test]
    fn trusted_identity_rejects_pid_reuse_cleanup_and_missing_process() {
        let root = test_root("identity-cleanup");
        let (executable, spawn) = process_fixture(&root);
        let tauri = tauri_fixture(&root);
        let handoff = TrustedProcessIdentity {
            pid: 30,
            parent_pid: Some(20),
            creation_time: Some(100_000_001),
            ..spawn.clone()
        };
        let trusted = trust(
            &spawn,
            &tauri,
            30,
            &executable,
            expected_instance_id(),
            &[handoff.clone(), tauri.clone()],
        )
        .expect("handoff should be trusted");
        let reused = TrustedProcessIdentity {
            creation_time: Some(999_999_999),
            ..handoff
        };
        assert!(!same_process_identity(&trusted.process, &reused));
        assert!(trust(
            &spawn,
            &tauri,
            999,
            &executable,
            expected_instance_id(),
            &[tauri.clone()],
        )
        .is_none());
        fs::remove_dir_all(root).expect("remove test root");
    }

    #[test]
    fn trusted_identity_rejects_cycles_and_excessive_depth() {
        let root = test_root("identity-bounds");
        let (executable, spawn) = process_fixture(&root);
        let tauri = tauri_fixture(&root);
        let cycle_a = TrustedProcessIdentity {
            pid: 11,
            parent_pid: Some(12),
            creation_time: Some(100_000_001),
            ..spawn.clone()
        };
        let cycle_b = TrustedProcessIdentity {
            pid: 12,
            parent_pid: Some(11),
            creation_time: Some(100_000_002),
            ..spawn.clone()
        };
        assert!(trust(
            &spawn,
            &tauri,
            11,
            &executable,
            expected_instance_id(),
            &[spawn.clone(), cycle_a, cycle_b],
        )
        .is_none());
        let mut deep = vec![spawn.clone()];
        for pid in 11..=(11 + MAX_PROCESS_ANCESTRY_DEPTH as u32) {
            deep.push(TrustedProcessIdentity {
                pid,
                parent_pid: Some(pid - 1),
                creation_time: Some(100_000_000 + u64::from(pid)),
                ..spawn.clone()
            });
        }
        assert!(trust(
            &spawn,
            &tauri,
            11 + MAX_PROCESS_ANCESTRY_DEPTH as u32,
            &executable,
            expected_instance_id(),
            &deep,
        )
        .is_none());
        fs::remove_dir_all(root).expect("remove test root");
    }

    #[test]
    fn readiness_probe_includes_dynamic_port_in_host() {
        let request = String::from_utf8(readiness_probe_request(49152, "/ready"))
            .expect("probe request is valid UTF-8");
        assert!(request.contains("GET /ready HTTP/1.1"));
        assert!(request.contains("Host: 127.0.0.1:49152"));
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

    #[test]
    fn startup_lock_acquires_without_existing_lock_and_releases_cleanly() {
        let root = test_root("startup-lock-clean");
        assert!(!root.join("startup.lock").exists());
        let lock = StartupLock::acquire(&root).expect("first launch should acquire");
        assert!(root.join("startup.lock").exists());
        drop(lock);
        assert!(!root.join("startup.lock").exists());
        let relaunch = StartupLock::acquire(&root).expect("relaunch should acquire");
        drop(relaunch);
        fs::remove_dir_all(root).expect("remove startup lock test root");
    }

    #[test]
    fn startup_lock_rejects_real_owner_without_panicking() {
        let root = test_root("startup-lock-contended");
        let owner = StartupLock::acquire(&root).expect("owner should acquire");
        let result = StartupLock::acquire(&root);
        assert!(matches!(result, Err(StartupLockError::Contended(_))));
        let diagnostics = fs::read_to_string(root.join("startup-lock-diagnostics.json"))
            .expect("contention diagnostics should be written");
        assert!(diagnostics.contains("rejected_contended"));
        drop(owner);
        fs::remove_dir_all(root).expect("remove startup lock test root");
    }

    #[test]
    fn startup_lock_recovers_a_stale_file() {
        let root = test_root("startup-lock-stale");
        fs::write(root.join("startup.lock"), b"stale pid=999999").expect("write stale lock");
        let lock = StartupLock::acquire(&root).expect("stale marker should not block launch");
        drop(lock);
        assert!(!root.join("startup.lock").exists());
        fs::remove_dir_all(root).expect("remove startup lock test root");
    }

    #[test]
    fn startup_lock_recovery_after_startup_failure_is_not_permanent() {
        let root = test_root("startup-lock-failure-recovery");
        let lock = StartupLock::acquire(&root).expect("launch should acquire");
        drop(lock);
        assert!(StartupLock::acquire(&root).is_ok());
        fs::remove_dir_all(root).expect("remove startup lock test root");
    }

    #[test]
    fn startup_lock_recovery_after_crash_simulation_is_safe() {
        let root = test_root("startup-lock-crash-recovery");
        {
            let _lock = StartupLock::acquire(&root).expect("launch should acquire");
        }
        fs::write(root.join("startup.lock"), b"orphaned crash marker")
            .expect("write crash residue");
        let recovered = StartupLock::acquire(&root).expect("crash residue should recover");
        drop(recovered);
        fs::remove_dir_all(root).expect("remove startup lock test root");
    }

    #[test]
    fn startup_lock_contention_is_a_normal_error_not_exit_101() {
        let root = test_root("startup-lock-expected-contention");
        let owner = StartupLock::acquire(&root).expect("owner should acquire");
        let error = StartupLock::acquire(&root).expect_err("second launch should be rejected");
        assert!(error.to_string().starts_with("STARTUP_LOCK_CONTENDED:"));
        drop(owner);
        fs::remove_dir_all(root).expect("remove startup lock test root");
    }

    #[test]
    fn startup_lock_diagnostics_are_privacy_safe_and_include_decision() {
        let root = test_root("startup-lock-diagnostics");
        let lock = StartupLock::acquire(&root).expect("launch should acquire");
        drop(lock);
        let diagnostics = fs::read_to_string(root.join("startup-lock-diagnostics.json"))
            .expect("startup lock diagnostics should exist");
        assert!(diagnostics.contains("released"));
        assert!(diagnostics.contains("startup_stopped"));
        assert!(!diagnostics.contains("sapsos.db"));
        fs::remove_dir_all(root).expect("remove startup lock test root");
    }

    #[test]
    fn startup_lock_concurrent_acquisition_has_one_owner() {
        let root = test_root("startup-lock-race");
        let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
        let first_root = root.clone();
        let first_barrier = barrier.clone();
        let first = thread::spawn(move || {
            let result = StartupLock::acquire(&first_root);
            let acquired = result.is_ok();
            first_barrier.wait();
            drop(result);
            acquired
        });
        let second_root = root.clone();
        let second_barrier = barrier.clone();
        let second = thread::spawn(move || {
            let result = StartupLock::acquire(&second_root);
            let acquired = result.is_ok();
            second_barrier.wait();
            drop(result);
            acquired
        });
        let acquired = [
            first.join().expect("first race worker"),
            second.join().expect("second race worker"),
        ];
        assert_eq!(acquired.iter().filter(|value| **value).count(), 1);
        fs::remove_dir_all(root).expect("remove startup lock test root");
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
            let api_manifest = match app
                .state::<DesktopProcesses>()
                .start(packaged_resource_dir.as_deref())
            {
                Ok(manifest) => manifest,
                Err(error) if error.starts_with("STARTUP_LOCK_CONTENDED:") => {
                    eprintln!("{error}");
                    app.handle().exit(0);
                    return Ok(());
                }
                Err(error) => return Err(Box::new(std::io::Error::other(error))),
            };

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
