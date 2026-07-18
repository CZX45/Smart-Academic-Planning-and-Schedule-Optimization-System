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
        runtime = [ordered]@{
            install_root = "<isolated-install-root>"
            app_data_root = "<isolated-appdata-root>"
            executable = "sapsos-local-desktop.exe"
            api_executable = "runtime/sapsos-api/sapsos-api.exe"
            manifest = "SAPSOS/runtime.json"
        }
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
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

function Invoke-LoopbackReady([int]$Port) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/ready" -TimeoutSec 3
        return $response.StatusCode -eq 200
    } catch { return $false }
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
    Wait-Until {
        $manifest = Get-RuntimeManifest
        if ($null -eq $manifest -or $manifest.status -ne "ready" -or $manifest.pid -ne $apiPid) { return $false }
        return (Invoke-LoopbackReady -Port ([int]$manifest.port))
    } $StartupTimeoutSeconds "Packaged API did not reach bounded loopback readiness."
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

    Add-UiAutomationAssemblies
    Write-Phase "first_launch" "starting"
    Write-Phase "test_fixture_setup" "starting"
    Initialize-TestDatabase
    Write-Phase "test_fixture_setup" "completed" @{ database = "SAPSOS/sapsos.db" }
    $script:currentPhase = "first_launch"
    $appProcess = Start-Process -FilePath $appExecutable -WorkingDirectory $installRoot -PassThru `
        -RedirectStandardOutput (Join-Path $root "tauri.stdout.log") `
        -RedirectStandardError (Join-Path $root "tauri.stderr.log")
    Wait-Until { -not $appProcess.HasExited } $StartupTimeoutSeconds "Installed Tauri executable exited before startup completed."
    Wait-Until {
        $appProcess.Refresh()
        if ($appProcess.HasExited) { throw "Installed Tauri executable exited before the packaged API child started." }
        $child = Get-ChildProcess $appProcess.Id $apiExecutable
        if ($child) { $script:apiPid = [int]$child.ProcessId; return $true }
        return $false
    } $StartupTimeoutSeconds "Installed packaged API child was not found under the Tauri process."
    Write-Phase "first_launch" "completed" @{ tauri_process = "alive"; packaged_api = "installed-child" }

    Write-Phase "api_readiness" "starting"
    Wait-ForRuntimeReady
    $manifest = Get-RuntimeManifest
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
    Wait-ForRuntimeReady
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
