$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$WebPort = if ($env:LOCAL_WEB_PORT) { $env:LOCAL_WEB_PORT } elseif ($env:PLAYWRIGHT_WEB_PORT) { $env:PLAYWRIGHT_WEB_PORT } else { "3000" }
$WebUrl = "http://localhost:$WebPort"
$ApiUrl = "http://localhost:8000"
$ApiDocsUrl = "http://localhost:8000/docs"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    Write-Host ""
    Write-Host $Message -ForegroundColor Cyan
    & $Action
}

function Wait-ForUrl {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSeconds = 90
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        try {
            $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 500) {
                Write-Host "[OK] $Name is reachable at $Url" -ForegroundColor Green
                return
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "$Name did not become reachable at $Url within $TimeoutSeconds seconds. Run: docker compose logs"
}

Push-Location $RepoRoot
try {
    Write-Host "Starting Smart Academic Planner from $RepoRoot"

    Invoke-Step "Checking prerequisites..." {
        & (Join-Path $ScriptDir "Check-Prerequisites.ps1")
    }

    Invoke-Step "Checking local environment file..." {
        if (-not (Test-Path ".env")) {
            if (-not (Test-Path ".env.example")) {
                throw ".env is missing and .env.example is not available."
            }
            Copy-Item ".env.example" ".env"
            Write-Host "[OK] Created .env from .env.example local development defaults." -ForegroundColor Green
        }
        else {
            Write-Host "[OK] .env already exists." -ForegroundColor Green
        }
    }

    Invoke-Step "Installing workspace dependencies if needed..." {
        if (-not (Test-Path "node_modules")) {
            corepack pnpm install --frozen-lockfile
            if ($LASTEXITCODE -ne 0) {
                throw "Dependency install failed. Check npm registry access and pnpm output."
            }
        }
        else {
            Write-Host "[OK] node_modules already exists." -ForegroundColor Green
        }
    }

    Invoke-Step "Starting PostgreSQL, API, and web app with Docker Compose..." {
        docker compose up -d --build
        if ($LASTEXITCODE -ne 0) {
                throw "Docker Compose startup failed. Confirm Docker Desktop is running and ports $WebPort, 8000, and 5432 are free."
        }
    }

    Invoke-Step "Waiting for local services..." {
        Wait-ForUrl "API health" "$ApiUrl/health"
        Wait-ForUrl "API docs" $ApiDocsUrl
        Wait-ForUrl "Web app" $WebUrl
    }

    Invoke-Step "Running development seed data..." {
        docker compose exec -T api python -m app.seed_dev
        if ($LASTEXITCODE -ne 0) {
            throw "Development seed failed. Check API logs with: docker compose logs api"
        }
        Write-Host "[OK] Development seed completed." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "Smart Academic Planner is running." -ForegroundColor Green
    Write-Host ""
    Write-Host "Web app:"
    Write-Host $WebUrl
    Write-Host ""
    Write-Host "API:"
    Write-Host $ApiUrl
    Write-Host ""
    Write-Host "API docs:"
    Write-Host $ApiDocsUrl
    Write-Host ""
    Write-Host "To stop:"
    Write-Host ".\scripts\windows\Stop-Smart-Academic-Planner.ps1"
}
catch {
    Write-Host ""
    Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Troubleshooting:"
    Write-Host "- Start Docker Desktop, then rerun this script."
    Write-Host "- Check ports $WebPort, 8000, and 5432 for conflicts."
    Write-Host "- Inspect logs with: docker compose logs"
    exit 1
}
finally {
    Pop-Location
}
