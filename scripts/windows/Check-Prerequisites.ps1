$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$Failures = 0

function Write-Check {
    param(
        [Parameter(Mandatory = $true)][string]$State,
        [Parameter(Mandatory = $true)][string]$Message
    )

    switch ($State) {
        "OK" { Write-Host "[OK] $Message" -ForegroundColor Green }
        "WARN" { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
        "FAIL" {
            Write-Host "[FAIL] $Message" -ForegroundColor Red
            $script:Failures += 1
        }
    }
}

function Test-Tool {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$InstallHint
    )

    $Command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($Command) {
        Write-Check "OK" "$Name found at $($Command.Source)"
        return $true
    }
    Write-Check "FAIL" "$Name was not found. $InstallHint"
    return $false
}

function Test-Port {
    param([Parameter(Mandatory = $true)][int]$Port)

    $Client = [System.Net.Sockets.TcpClient]::new()
    try {
        $AsyncResult = $Client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $Connected = $AsyncResult.AsyncWaitHandle.WaitOne(250, $false)
        if ($Connected) {
            $Client.EndConnect($AsyncResult)
            Write-Check "WARN" "Port $Port is already accepting connections. This is fine if SAPSOS is already running."
            return
        }
        Write-Check "OK" "Port $Port is available."
    }
    catch {
        Write-Check "OK" "Port $Port is available."
    }
    finally {
        $Client.Dispose()
    }
}

Push-Location $RepoRoot
try {
    Write-Host "Checking Smart Academic Planner prerequisites from $RepoRoot"
    Write-Host ""

    $HasGit = Test-Tool "git" "Install Git for Windows from https://git-scm.com/."
    if ($HasGit) {
        $GitVersion = git --version
        Write-Check "OK" $GitVersion
    }

    $HasNode = Test-Tool "node" "Install Node.js 24 or newer from https://nodejs.org/."
    if ($HasNode) {
        $NodeVersion = node --version
        Write-Check "OK" "Node.js $NodeVersion"
    }

    $HasCorepack = Test-Tool "corepack" "Install a current Node.js release that includes Corepack."
    if ($HasCorepack) {
        $CorepackVersion = corepack --version
        Write-Check "OK" "Corepack $CorepackVersion"
        try {
            $PnpmVersion = corepack pnpm --version
            Write-Check "OK" "pnpm $PnpmVersion through Corepack"
        }
        catch {
            Write-Check "FAIL" "pnpm through Corepack is unavailable. Run: corepack enable"
        }
    }

    $HasPython = Test-Tool "python" "Install Python 3.12 or newer for backend checks outside Docker."
    if ($HasPython) {
        $PythonVersion = python --version
        Write-Check "OK" $PythonVersion
    }

    $HasDocker = Test-Tool "docker" "Install Docker Desktop and start it before running the local stack."
    if ($HasDocker) {
        $DockerVersion = docker --version
        Write-Check "OK" $DockerVersion
        try {
            docker compose version | Out-Null
            Write-Check "OK" "Docker Compose is available."
        }
        catch {
            Write-Check "FAIL" "Docker Compose is unavailable. Update Docker Desktop."
        }
        try {
            docker info | Out-Null
            Write-Check "OK" "Docker daemon is running."
        }
        catch {
            Write-Check "FAIL" "Docker Desktop is not running. Please start Docker Desktop and try again."
        }
    }

    if (Test-Path ".env") {
        Write-Check "OK" ".env exists."
    }
    elseif (Test-Path ".env.example") {
        Write-Check "WARN" ".env is missing. Start-Smart-Academic-Planner.ps1 can create it from .env.example."
    }
    else {
        Write-Check "FAIL" ".env.example is missing. Cannot create safe local defaults."
    }

    foreach ($Port in @(3000, 8000, 5432)) {
        Test-Port $Port
    }

    if ($Failures -gt 0) {
        Write-Host ""
        Write-Host "Prerequisite check failed with $Failures issue(s)." -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "Prerequisite check passed." -ForegroundColor Green
}
finally {
    Pop-Location
}
