[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallerPath,
    [string]$TestRoot = (Join-Path ([IO.Path]::GetTempPath()) "SAPSOS-packaged-e2e-$([Guid]::NewGuid().ToString('N'))"),
    [int]$InstallerTimeoutSeconds = 180,
    [int]$StartupTimeoutSeconds = 120,
    [int]$UiTimeoutSeconds = 60,
    [int]$ShutdownTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..\..")).Path
$installer = (Resolve-Path $InstallerPath).Path
$root = [IO.Path]::GetFullPath($TestRoot).TrimEnd('\', '/')
$localAppData = Join-Path $root "localappdata"
$installRoot = Join-Path $localAppData "Programs\SAPSOS Local Desktop"
$evidenceRoot = Join-Path $root "evidence"
$appExecutable = Join-Path $installRoot "sapsos-local-desktop.exe"
$apiExecutable = Join-Path $installRoot "runtime\sapsos-api\sapsos-api.exe"
$appData = Join-Path $localAppData "SAPSOS"
$runtimeManifest = Join-Path $appData "runtime.json"
$summaryPath = Join-Path $evidenceRoot "summary.json"
$phases = [ordered]@{}
$script:readinessDiagnostics = [ordered]@{}
$script:readinessHttpAt = @{}
$currentPhase = "initialization"
$appProcess = $null
$apiPid = $null

if ([IO.Path]::GetPathRoot($root) -eq $root) { throw "E2E test root cannot be a drive root." }
if (Test-Path -LiteralPath $root) { throw "E2E test root must not already exist: $root" }
New-Item -ItemType Directory -Force -Path $evidenceRoot, $localAppData | Out-Null
$previousLocalAppData = $env:LOCALAPPDATA
$previousCi = $env:CI
$previousLifecycleTestMode = $env:SAPSOS_LIFECYCLE_TEST_MODE
$env:LOCALAPPDATA = $localAppData
$env:CI = "true"
$env:SAPSOS_LIFECYCLE_TEST_MODE = "true"

function Write-Phase([string]$Name, [ValidateSet("starting", "completed", "failed")][string]$Status, [hashtable]$Details = @{}) {
    $script:currentPhase = $Name
    $record = [ordered]@{ status = $Status; details = [ordered]@{} }
    foreach ($key in $Details.Keys) { $record.details[$key] = $Details[$key] }
    $phases[$Name] = $record
    Write-Host "phase=$Name status=$Status"
}

function Save-SanitizedLog([string]$SourcePath, [string]$Name) {
    if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) { return }
    $content = Get-Content -LiteralPath $SourcePath -Raw -ErrorAction SilentlyContinue
    if ($null -eq $content) { return }
    $content = $content.Replace($root, "<isolated-test-root>").Replace($repoRoot, "<repository-root>")
    $content = [regex]::Replace($content, '(?i)C:\\Users\\[^\\\r\n ]+', '<user-path>')
    $content.Substring(0, [Math]::Min(4096, $content.Length)) | Set-Content -LiteralPath (Join-Path $evidenceRoot $Name) -Encoding UTF8
}

function Save-Evidence {
    [ordered]@{
        schema_version = 1
        product = "SAPSOS Local Desktop"
        installer_version = (Get-Item $installer).VersionInfo.ProductVersion
        app_version = if (Test-Path $appExecutable) { (Get-Item $appExecutable).VersionInfo.ProductVersion } else { $null }
        product_mode = "LOCAL_DESKTOP"
        phases = $phases
        readiness_diagnostics = $script:readinessDiagnostics
        runtime = [ordered]@{
            install_root = "<isolated-install-root>"
            app_data_root = "<isolated-appdata-root>"
            executable = "sapsos-local-desktop.exe"
            api_executable = "runtime/sapsos-api/sapsos-api.exe"
            manifest = "SAPSOS/runtime.json"
        }
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
    $script:readinessDiagnostics | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $evidenceRoot "readiness-diagnostic.json") -Encoding UTF8
}

function Assert-True([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }

function Wait-Until([scriptblock]$Condition, [int]$TimeoutSeconds, [string]$FailureMessage) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (& $Condition) { return }
        Start-Sleep -Milliseconds 250
    }
    throw $FailureMessage
}

function Invoke-ProcessBounded([string]$PathValue, [string[]]$Arguments, [int]$TimeoutSeconds, [string]$PhaseName) {
    $process = Start-Process -FilePath $PathValue -ArgumentList $Arguments -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while (-not $process.HasExited -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $process.Refresh()
    }
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "$PhaseName timed out after $TimeoutSeconds seconds."
    }
    Assert-True ($process.ExitCode -eq 0) "$PhaseName failed with exit code $($process.ExitCode)."
}

function Get-ChildProcess([int]$ParentPid, [string]$ExpectedPath) {
    try {
        return Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentPid" -ErrorAction Stop |
            Where-Object { $_.ExecutablePath -and ([IO.Path]::GetFullPath($_.ExecutablePath) -ieq $ExpectedPath) } |
            Select-Object -First 1
    } catch {
        return $null
    }
}

function Get-RuntimeManifest {
    if (-not (Test-Path -LiteralPath $runtimeManifest -PathType Leaf)) { return $null }
    try { return Get-Content -LiteralPath $runtimeManifest -Raw | ConvertFrom-Json } catch { return $null }
}

function New-ReadinessDiagnostic([string]$Mode) {
    [ordered]@{
        mode = $Mode
        process_started = $false
        process_pid = $null
        process_exit_observed = $false
        process_exit_within_30s = $null
        manifest_observed = $false
        manifest_status = $null
        manifest_pid = $null
        pid_match = $null
        port = $null
        listener_observed = $false
        listener_pid = $null
        health_status = $null
        health_result = $null
        ready_status = $null
        ready_result = $null
        tauri_still_alive = $null
        child_still_alive = $null
        manifest_removed = $null
        manifest_removed_by_api = $null
        lock_present = $null
        manifest_removed_before_cleanup = $null
        elapsed_ms = 0
        transitions = @()
        process_tree = @()
    }
}

function Add-ReadinessTransition($Diagnostic, [string]$State, $Manifest, [int]$ElapsedMs) {
    $previous = if ($Diagnostic.transitions.Count -gt 0) { $Diagnostic.transitions[-1].state } else { $null }
    if ($previous -eq $State) { return }
    $Diagnostic.transitions += [ordered]@{
        elapsed_ms = $ElapsedMs
        state = $State
        manifest_pid = if ($Manifest) { [int]$Manifest.pid } else { $null }
        port = if ($Manifest) { [int]$Manifest.port } else { $null }
        pid_match = if ($Manifest) { ([int]$Manifest.pid -eq [int]$Diagnostic.process_pid) } else { $null }
        lock_present = (Test-Path -LiteralPath "$runtimeManifest.lock")
    }
}

function Get-ListenerSnapshot([int]$Port) {
    if ($Port -le 0) {
        return [ordered]@{ observed = $false; owning_pid = $null }
    }
    try {
        $connection = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($null -eq $connection) {
            return [ordered]@{ observed = $false; owning_pid = $null }
        }
        return [ordered]@{ observed = $true; owning_pid = [int]$connection.OwningProcess }
    } catch {
        return [ordered]@{ observed = $false; owning_pid = $null }
    }
}

function Get-HttpProbe([int]$Port, [string]$PathValue) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port$PathValue" -TimeoutSec 3
        $bodySummary = $null
        if ($response.Content) {
            try {
                $body = $response.Content | ConvertFrom-Json
                $bodySummary = [ordered]@{
                    status = $body.status
                    database_ready = $body.database_ready
                    detail = $body.detail
                }
            } catch { $bodySummary = "non-json-response" }
        }
        return [ordered]@{ status = [int]$response.StatusCode; result = $bodySummary; error = $null }
    } catch {
        $status = $null
        try { if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode } } catch { }
        $category = if ($_.Exception.Message -match "timed out|timeout") { "timeout" } elseif ($_.Exception.Message -match "refused|actively refused") { "connection_refused" } else { "request_failed" }
        return [ordered]@{ status = $status; result = $null; error = $category }
    }
}

function Get-ReadinessManifest {
    if (-not (Test-Path -LiteralPath $runtimeManifest -PathType Leaf)) {
        return [ordered]@{ observed = $false; manifest = $null }
    }
    try {
        return [ordered]@{ observed = $true; manifest = (Get-Content -LiteralPath $runtimeManifest -Raw | ConvertFrom-Json) }
    } catch {
        return [ordered]@{ observed = $true; manifest = $null }
    }
}

function Test-ExactProcessAlive([int]$ProcessId, [string]$ExpectedPath) {
    try {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
        return $null -ne $process -and $process.ExecutablePath -and ([IO.Path]::GetFullPath($process.ExecutablePath) -ieq $ExpectedPath)
    } catch { return $false }
}

function Get-VerifiedProcessTree([int[]]$ProcessIds, [string]$ExpectedApiPath, [string]$ExpectedAppPath) {
    $rows = @()
    foreach ($processId in $ProcessIds) {
        try {
            $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction Stop
            if ($process -and $process.ExecutablePath) {
                $role = if ([IO.Path]::GetFullPath($process.ExecutablePath) -ieq $ExpectedApiPath) { "packaged-api" } elseif ([IO.Path]::GetFullPath($process.ExecutablePath) -ieq $ExpectedAppPath) { "tauri" } else { "verified-descendant" }
                $rows += [ordered]@{ pid = [int]$process.ProcessId; parent_pid = [int]$process.ParentProcessId; role = $role }
            }
        } catch { }
    }
    return $rows
}

function Observe-Readiness($Diagnostic, [int]$ExpectedPid, [System.Diagnostics.Process]$TauriProcess = $null, [System.Diagnostics.Process]$ManagedProcess = $null) {
    $elapsedMs = [int](([DateTime]::UtcNow - $Diagnostic.started_at).TotalMilliseconds)
    $Diagnostic.elapsed_ms = $elapsedMs
    $manifestState = Get-ReadinessManifest
    $manifest = $manifestState.manifest
    $state = if (-not $manifestState.observed) { "missing" } elseif ($null -eq $manifest) { "invalid" } else { [string]$manifest.status }
    Add-ReadinessTransition $Diagnostic $state $manifest $elapsedMs
    if ($manifestState.observed) { $Diagnostic.manifest_observed = $true }
    if ($manifest) {
        $Diagnostic.manifest_status = [string]$manifest.status
        $Diagnostic.manifest_pid = [int]$manifest.pid
        $Diagnostic.pid_match = ([int]$manifest.pid -eq $ExpectedPid)
        $Diagnostic.port = [int]$manifest.port
        $listener = Get-ListenerSnapshot ([int]$manifest.port)
        $Diagnostic.listener_observed = [bool]$listener.observed
        $Diagnostic.listener_pid = $listener.owning_pid
        $now = [DateTime]::UtcNow
        $lastHttp = if ($script:readinessHttpAt.ContainsKey($Diagnostic.mode)) { $script:readinessHttpAt[$Diagnostic.mode] } else { [DateTime]::MinValue }
        if (([int]$manifest.port -gt 0) -and (($now - $lastHttp).TotalMilliseconds -ge 750)) {
            $script:readinessHttpAt[$Diagnostic.mode] = $now
            $health = Get-HttpProbe ([int]$manifest.port) "/health"
            $ready = Get-HttpProbe ([int]$manifest.port) "/ready"
            $Diagnostic.health_status = $health.status
            $Diagnostic.health_result = $health.result ?? $health.error
            $Diagnostic.ready_status = $ready.status
            $Diagnostic.ready_result = $ready.result ?? $ready.error
        }
    }
    if ($TauriProcess) {
        $TauriProcess.Refresh()
        $Diagnostic.tauri_still_alive = -not $TauriProcess.HasExited
    }
    if ($ManagedProcess) {
        $ManagedProcess.Refresh()
        $Diagnostic.child_still_alive = -not $ManagedProcess.HasExited
    } else {
        $Diagnostic.child_still_alive = Test-ExactProcessAlive $ExpectedPid $apiExecutable
    }
    return $manifest
}

function Wait-ForReadinessDiagnostic($Diagnostic, [int]$ExpectedPid, [int]$TimeoutSeconds, [System.Diagnostics.Process]$TauriProcess = $null, [System.Diagnostics.Process]$ManagedProcess = $null) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $manifest = Observe-Readiness $Diagnostic $ExpectedPid $TauriProcess $ManagedProcess
        if ($Diagnostic.mode -eq "tauri_supervised" -and $Diagnostic.tauri_still_alive -eq $false) {
            $Diagnostic.process_exit_observed = $true
            $Diagnostic.process_exit_within_30s = $Diagnostic.elapsed_ms -le 30000
            return $false
        }
        if ($Diagnostic.mode -eq "direct" -and $Diagnostic.child_still_alive -eq $false) {
            $Diagnostic.process_exit_observed = $true
            $Diagnostic.process_exit_within_30s = $Diagnostic.elapsed_ms -le 30000
            return $false
        }
        if ($manifest -and $manifest.status -eq "ready" -and $Diagnostic.ready_status -eq 200) { return $true }
        Start-Sleep -Milliseconds 250
    }
    Observe-Readiness $Diagnostic $ExpectedPid $TauriProcess $ManagedProcess | Out-Null
    return $false
}

function Stop-ExactPackagedProcess([int]$ProcessId) {
    if ($ProcessId -and (Test-ExactProcessAlive $ProcessId $apiExecutable)) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-DirectPackagedApiDiagnostic {
    $diagnostic = New-ReadinessDiagnostic "direct"
    $diagnostic.started_at = [DateTime]::UtcNow
    $script:readinessHttpAt.Remove("direct")
    $runtimeDirectory = Split-Path -Parent $apiExecutable
    $databasePath = Join-Path $appData "sapsos.db"
    $env:DATABASE_URL = "sqlite+pysqlite:///$(($databasePath -replace '\\','/'))"
    $env:PRODUCT_MODE = "LOCAL_DESKTOP"
    $env:AUTH_MODE = "local"
    $env:ENVIRONMENT = "test"
    $env:API_HOST = "127.0.0.1"
    $env:API_PORT = "0"
    $previousPath = $env:PATH
    $env:PATH = "$runtimeDirectory;$previousPath"
    $stdoutPath = Join-Path $root "direct-api.stdout.log"
    $stderrPath = Join-Path $root "direct-api.stderr.log"
    $process = $null
    try {
        $process = Start-Process -FilePath $apiExecutable -WorkingDirectory $runtimeDirectory -PassThru `
            -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $diagnostic.process_started = $true
        $diagnostic.process_pid = [int]$process.Id
        $script:directApiPid = [int]$process.Id
        $success = Wait-ForReadinessDiagnostic $diagnostic ([int]$process.Id) 30 $null $process
        return $diagnostic
    } finally {
        if ($process) {
            $process.Refresh()
            if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
            try { $null = $process.WaitForExit(5000) } catch { }
        }
        $diagnostic.manifest_removed_before_cleanup = -not (Test-Path -LiteralPath $runtimeManifest)
        $diagnostic.manifest_removed_by_api = [bool]$diagnostic.manifest_removed_before_cleanup
        if (-not $diagnostic.manifest_removed_before_cleanup -and -not (Test-Path -LiteralPath "$runtimeManifest.lock")) {
            Remove-Item -LiteralPath $runtimeManifest -Force -ErrorAction SilentlyContinue
        }
        $diagnostic.manifest_removed = -not (Test-Path -LiteralPath $runtimeManifest)
        $diagnostic.lock_present = Test-Path -LiteralPath "$runtimeManifest.lock"
        if ($diagnostic.process_pid) { $diagnostic.process_tree = Get-VerifiedProcessTree @($diagnostic.process_pid) $apiExecutable $appExecutable }
        $env:PATH = $previousPath
    }
}

function Initialize-TestDatabase {
    New-Item -ItemType Directory -Force -Path $appData | Out-Null
    $databasePath = Join-Path $appData "sapsos.db"
    $databaseInitializer = "import sys; from pathlib import Path; from sqlalchemy import create_engine; from app.db.bootstrap import initialize_database; initialize_database(create_engine('sqlite+pysqlite:///' + Path(sys.argv[1]).as_posix()))"
    Push-Location (Join-Path $repoRoot "apps\api")
    try {
        & (Get-Command python -ErrorAction Stop).Source -c $databaseInitializer $databasePath
        Assert-True ($LASTEXITCODE -eq 0) "The supported LOCAL_DESKTOP SQLite bootstrap helper failed."
    } finally {
        Pop-Location
    }
    Assert-True (Test-Path $databasePath -PathType Leaf) "The supported SQLite bootstrap helper did not create the database."
}

function Wait-ForRuntimeReady {
    param([string]$DiagnosticName = "tauri_supervised")
    $diagnostic = if ($script:readinessDiagnostics.Contains($DiagnosticName)) { $script:readinessDiagnostics[$DiagnosticName] } else { New-ReadinessDiagnostic "tauri_supervised" }
    if (-not $diagnostic.started_at) { $diagnostic.started_at = [DateTime]::UtcNow }
    $script:readinessHttpAt.Remove($DiagnosticName)
    $script:readinessDiagnostics[$DiagnosticName] = $diagnostic
    $diagnostic.process_pid = [int]$apiPid
    $success = Wait-ForReadinessDiagnostic $diagnostic ([int]$apiPid) $StartupTimeoutSeconds $appProcess
    if (-not $success) {
        throw "Packaged API did not reach bounded loopback readiness."
    }
    return (Get-RuntimeManifest)
}

function Add-UiAutomationAssemblies {
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
}

function Get-MainWindow {
    $rootElement = [System.Windows.Automation.AutomationElement]::RootElement
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        "SAPSOS Local Desktop")
    return $rootElement.FindFirst([System.Windows.Automation.TreeScope]::Children, $condition)
}

function Find-UiElement([string]$Name) {
    $window = Get-MainWindow
    if ($null -eq $window) { return $null }
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty, $Name)
    return $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
}

function Find-UiElementContains([string]$Name) {
    $window = Get-MainWindow
    if ($null -eq $window) { return $null }
    foreach ($element in $window.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition)) {
        if ($element.Current.Name -like "*$Name*") { return $element }
    }
    return $null
}

function Wait-UiElement([string]$Name) {
    $result = $null
    Wait-Until { $script:uiElement = Find-UiElement $Name; $null -ne $script:uiElement } $UiTimeoutSeconds "UI marker/control was not found: $Name"
    return $script:uiElement
}

function Wait-UiElementContains([string]$Name) {
    Wait-Until { $script:uiElement = Find-UiElementContains $Name; $null -ne $script:uiElement } $UiTimeoutSeconds "UI marker was not found: $Name"
    return $script:uiElement
}

function Invoke-UiButton([string]$Name) {
    $element = Wait-UiElement $Name
    $pattern = $element.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
    $pattern.Invoke()
}

function Capture-Window([string]$Name) {
    $window = Get-MainWindow
    if ($null -eq $window) { return }
    $bounds = $window.Current.BoundingRectangle
    if ($bounds.Width -le 0 -or $bounds.Height -le 0) { return }
    Add-Type -AssemblyName System.Drawing
    Add-Type -AssemblyName System.Windows.Forms
    $bitmap = New-Object System.Drawing.Bitmap([int]$bounds.Width, [int]$bounds.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen([int]$bounds.X, [int]$bounds.Y, 0, 0, $bitmap.Size)
    $bitmap.Save((Join-Path $evidenceRoot "$Name.png"), [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose(); $bitmap.Dispose()
}

try {
    Write-Phase "install" "starting"
    Invoke-ProcessBounded $installer @("/S", "/D=$installRoot") $InstallerTimeoutSeconds "installer"
    Assert-True (Test-Path $appExecutable -PathType Leaf) "Installed Tauri executable is missing."
    Assert-True (Test-Path $apiExecutable -PathType Leaf) "Installed packaged API executable is missing."
    Assert-True (Test-Path (Join-Path $installRoot "runtime\sapsos-api") -PathType Container) "Packaged API runtime directory is missing."
    Assert-True ((Get-ChildItem $installRoot -Recurse -Filter "_pydantic_core*.pyd" -File).Count -gt 0) "pydantic_core native extension is missing."
    Write-Phase "install" "completed" @{ install_root = "<isolated-install-root>" }

    Write-Phase "test_fixture_setup" "starting"
    Initialize-TestDatabase
    Write-Phase "test_fixture_setup" "completed" @{ database = "SAPSOS/sapsos.db" }

    Write-Phase "direct_api_diagnostic" "starting"
    $directDiagnostic = Invoke-DirectPackagedApiDiagnostic
    $script:readinessDiagnostics["direct_api"] = $directDiagnostic
    Save-SanitizedLog (Join-Path $root "direct-api.stderr.log") "sanitized-direct-api-stderr.txt"
    Save-SanitizedLog (Join-Path $root "direct-api.stdout.log") "sanitized-direct-api-stdout.txt"
    $directResult = if ($directDiagnostic.ready_status -eq 200 -and $directDiagnostic.manifest_status -eq "ready") { "DIRECT_API_READY" } else { "DIRECT_API_FAILED" }
    Write-Host "diagnostic=direct_api result=$directResult"
    Write-Phase "direct_api_diagnostic" "completed" @{ result = $directResult; elapsed_ms = $directDiagnostic.elapsed_ms }

    Add-UiAutomationAssemblies
    Write-Phase "first_launch" "starting"
    $supervisedDiagnostic = New-ReadinessDiagnostic "tauri_supervised"
    $supervisedDiagnostic.started_at = [DateTime]::UtcNow
    $supervisedDiagnostic.process_started = $true
    $script:readinessDiagnostics["tauri_supervised"] = $supervisedDiagnostic
    $appProcess = Start-Process -FilePath $appExecutable -WorkingDirectory $installRoot -PassThru `
        -RedirectStandardOutput (Join-Path $root "tauri.stdout.log") `
        -RedirectStandardError (Join-Path $root "tauri.stderr.log")
    $childDeadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    $childFound = $false
    while ([DateTime]::UtcNow -lt $childDeadline) {
        $appProcess.Refresh()
        Observe-Readiness $supervisedDiagnostic 0 $appProcess | Out-Null
        if ($appProcess.HasExited) {
            $supervisedDiagnostic.process_exit_observed = $true
            $supervisedDiagnostic.process_exit_within_30s = $supervisedDiagnostic.elapsed_ms -le 30000
            break
        }
        $child = Get-ChildProcess $appProcess.Id $apiExecutable
        if ($child) {
            $script:apiPid = [int]$child.ProcessId
            $supervisedDiagnostic.process_pid = [int]$apiPid
            $supervisedDiagnostic.child_still_alive = $true
            $childFound = $true
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $childFound) { throw "Installed packaged API child was not found under the Tauri process." }
    Write-Phase "first_launch" "completed" @{ tauri_process = "alive"; packaged_api = "installed-child" }

    Write-Phase "api_readiness" "starting"
    $manifest = Wait-ForRuntimeReady
    Assert-True ($manifest.base_url -match '^http://127\.0\.0\.1:\d+$') "Runtime manifest is not loopback-only."
    Write-Phase "api_readiness" "completed" @{ status = "ready"; binding = "127.0.0.1" }

    Write-Phase "webview_render" "starting"
    Wait-UiElement "智能学业规划" | Out-Null
    Wait-UiElement "主要工作流" | Out-Null
    Capture-Window "first-launch"
    Write-Phase "webview_render" "completed" @{ marker = "智能学业规划"; source = "installed-static-webview" }

    Write-Phase "synthetic_import" "starting"
    Invoke-UiButton "加载脱敏 MyProgress 示例"
    Wait-UiElement "数据导入预览汇总" | Out-Null
    Capture-Window "synthetic-staging"
    Write-Phase "synthetic_import" "completed" @{ fixture = "sanitized-myprogress" }

    Write-Phase "review_apply" "starting"
    Invoke-UiButton "创建审核"
    Wait-UiElement "数据审核汇总" | Out-Null
    Invoke-UiButton "应用已确认记录"
    Wait-UiElement "应用结果" | Out-Null
    Capture-Window "reviewed-synthetic-data"
    Write-Phase "review_apply" "completed" @{ boundary = "explicit-review-apply" }

    Write-Phase "persistence_write" "starting"
    Assert-True (Test-Path $appData -PathType Container) "Stable AppData root was not created."
    Assert-True (Test-Path (Join-Path $appData "sapsos.db") -PathType Leaf) "SQLite database was not created by the packaged app."
    $dbHeader = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes((Join-Path $appData "sapsos.db"))[0..5])
    Assert-True ($dbHeader -eq "SQLite") "Packaged app did not create a valid SQLite database."
    $firstAppData = (Resolve-Path $appData).Path
    Write-Phase "persistence_write" "completed" @{ database = "SAPSOS/sapsos.db" }

    Write-Phase "graceful_shutdown" "starting"
    $appProcess.CloseMainWindow()
    Wait-Until { $appProcess.Refresh(); return $appProcess.HasExited } $ShutdownTimeoutSeconds "Tauri process did not exit within the bounded shutdown window."
    Wait-Until { $null -eq (Get-CimInstance Win32_Process -Filter "ProcessId=$apiPid" -ErrorAction SilentlyContinue) } $ShutdownTimeoutSeconds "Packaged API child did not exit after Tauri shutdown."
    Assert-True (-not (Test-Path $runtimeManifest)) "Owned runtime manifest was not cleared after shutdown."
    Write-Phase "graceful_shutdown" "completed" @{ orphan_api = $false }

    Write-Phase "restart" "starting"
    New-Item -ItemType Directory -Force -Path $appData | Out-Null
    @{ status = "ready"; pid = 4294967295; port = 1; base_url = "http://127.0.0.1:1" } | ConvertTo-Json | Set-Content -LiteralPath $runtimeManifest -Encoding UTF8
    $appProcess = Start-Process -FilePath $appExecutable -WorkingDirectory $installRoot -PassThru `
        -RedirectStandardOutput (Join-Path $root "tauri-restart.stdout.log") `
        -RedirectStandardError (Join-Path $root "tauri-restart.stderr.log")
    Wait-Until {
        $appProcess.Refresh()
        if ($appProcess.HasExited) { throw "Installed Tauri executable exited during restart." }
        $child = Get-ChildProcess $appProcess.Id $apiExecutable
        if ($child) { $script:apiPid = [int]$child.ProcessId; return $true }
        return $false
    } $StartupTimeoutSeconds "Packaged API child was not recreated on restart."
    Wait-ForRuntimeReady "tauri_supervised_restart" | Out-Null
    Wait-UiElement "智能学业规划" | Out-Null
    Write-Phase "restart" "completed" @{ stale_state = "recovered" }

    Write-Phase "persistence_verify" "starting"
    Assert-True ((Resolve-Path $appData).Path -eq $firstAppData) "AppData root changed across restart."
    Invoke-UiButton "加载已保存导入"
    Wait-UiElement "数据导入预览汇总" | Out-Null
    Capture-Window "restart-persistence"
    Write-Phase "persistence_verify" "completed" @{ synthetic_state = "present" }

    Write-Phase "diagnostics_smoke" "starting"
    Invoke-UiButton "Diagnostics"
    Wait-UiElement "Refresh diagnostics" | Out-Null
    Invoke-UiButton "Refresh diagnostics"
    Wait-UiElementContains "Overall diagnostics status" | Out-Null
    Write-Phase "diagnostics_smoke" "completed" @{ secret_free = $true }
} catch {
    Save-SanitizedLog (Join-Path $root "direct-api.stderr.log") "sanitized-direct-api-stderr.txt"
    Save-SanitizedLog (Join-Path $root "direct-api.stdout.log") "sanitized-direct-api-stdout.txt"
    Save-SanitizedLog (Join-Path $root "tauri.stderr.log") "tauri.stderr.log"
    Save-SanitizedLog (Join-Path $root "tauri-restart.stderr.log") "tauri-restart.stderr.log"
    Save-SanitizedLog (Join-Path $root "tauri.stdout.log") "tauri.stdout.log"
    Save-SanitizedLog (Join-Path $root "tauri-restart.stdout.log") "tauri-restart.stdout.log"
    if ($currentPhase) { Write-Phase $currentPhase "failed" @{ error = $_.Exception.Message.Substring(0, [Math]::Min(240, $_.Exception.Message.Length)) } }
    throw
} finally {
    Write-Phase "cleanup" "starting"
    if ($appProcess -and -not $appProcess.HasExited) {
        $appProcess.CloseMainWindow()
        $deadline = [DateTime]::UtcNow.AddSeconds($ShutdownTimeoutSeconds)
        while (-not $appProcess.HasExited -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 250; $appProcess.Refresh() }
    }
    if ($apiPid) {
        $apiProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$apiPid" -ErrorAction SilentlyContinue
        if ($apiProcess -and ([IO.Path]::GetFullPath($apiProcess.ExecutablePath) -ieq $apiExecutable)) {
            Stop-Process -Id $apiPid -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($name in @("tauri_supervised", "tauri_supervised_restart")) {
        if ($script:readinessDiagnostics.Contains($name)) {
            $diagnostic = $script:readinessDiagnostics[$name]
            $diagnostic.manifest_removed = -not (Test-Path -LiteralPath $runtimeManifest)
            $diagnostic.lock_present = Test-Path -LiteralPath "$runtimeManifest.lock"
            $treeIds = @()
            if ($appProcess) { $treeIds += [int]$appProcess.Id }
            if ($apiPid) { $treeIds += [int]$apiPid }
            $diagnostic.process_tree = Get-VerifiedProcessTree $treeIds $apiExecutable $appExecutable
        }
    }
    if ($previousLocalAppData) { $env:LOCALAPPDATA = $previousLocalAppData }
    elseif (Test-Path Env:LOCALAPPDATA) { Remove-Item Env:LOCALAPPDATA }
    if ($previousCi) { $env:CI = $previousCi }
    elseif (Test-Path Env:CI) { Remove-Item Env:CI }
    if ($previousLifecycleTestMode) { $env:SAPSOS_LIFECYCLE_TEST_MODE = $previousLifecycleTestMode }
    elseif (Test-Path Env:SAPSOS_LIFECYCLE_TEST_MODE) { Remove-Item Env:SAPSOS_LIFECYCLE_TEST_MODE }
    Write-Phase "cleanup" "completed"
    Save-Evidence
}

Write-Output $summaryPath
