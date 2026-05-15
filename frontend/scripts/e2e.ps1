$ErrorActionPreference = "Stop"

$frontendPort = if ($env:E2E_FRONTEND_PORT) { [int]$env:E2E_FRONTEND_PORT } else { 3100 }
$backendPort = if ($env:E2E_BACKEND_PORT) { [int]$env:E2E_BACKEND_PORT } else { 8100 }
$frontendUrl = "http://127.0.0.1:$frontendPort"
$backendUrl = "http://127.0.0.1:$backendPort/api/artifacts/providers/status"
$repoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = (Resolve-Path "$PSScriptRoot\..").Path
$e2eDatabaseDir = Join-Path $frontendDir "test-results"
$e2eDatabasePath = Join-Path $e2eDatabaseDir "meeting_assistant_e2e_$PID.db"
$e2eDatabaseUriPath = ($e2eDatabasePath -replace "\\", "/")
$e2eDatabaseUrl = if ($env:E2E_DATABASE_URL) { $env:E2E_DATABASE_URL } else { "sqlite:///$e2eDatabaseUriPath" }
$removeE2eDatabase = -not $env:E2E_DATABASE_URL

function Wait-ForUrl {
  param(
    [string]$Url,
    [int]$TimeoutSeconds = 60
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        return
      }
    } catch {
      Start-Sleep -Milliseconds 500
    }
  }

  throw "Timed out waiting for $Url"
}

$python = (Get-Command python).Source
$nodeDir = Split-Path (Get-Command node).Source
$npx = Join-Path $nodeDir "npx.cmd"
$backend = $null
$frontend = $null
$exitCode = 1

try {
  $backendEnv = @{
    CALENDAR_BACKGROUND_SYNC_ENABLED = "false"
    DATABASE_URL = $e2eDatabaseUrl
  }
  foreach ($key in $backendEnv.Keys) {
    Set-Item -Path "Env:$key" -Value $backendEnv[$key]
  }

  if (-not (Test-Path $e2eDatabaseDir)) {
    New-Item -ItemType Directory -Path $e2eDatabaseDir | Out-Null
  }

  Write-Host "E2E database: $e2eDatabaseUrl"

  if ($removeE2eDatabase -and (Test-Path $e2eDatabasePath)) {
    Remove-Item -LiteralPath $e2eDatabasePath -Force -ErrorAction SilentlyContinue
  }

  Push-Location $backendDir
  try {
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
      throw "Alembic migration failed for the E2E database."
    }
  } finally {
    Pop-Location
  }

  $backend = Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$backendPort") `
    -WorkingDirectory $backendDir `
    -PassThru `
    -WindowStyle Hidden

  Wait-ForUrl -Url $backendUrl -TimeoutSeconds 45

  $env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:$backendPort/api"
  $frontend = Start-Process `
    -FilePath $npx `
    -ArgumentList @("next", "dev", "--hostname", "127.0.0.1", "--port", "$frontendPort") `
    -WorkingDirectory $frontendDir `
    -PassThru `
    -WindowStyle Hidden

  Wait-ForUrl -Url $frontendUrl -TimeoutSeconds 75

  $env:E2E_START_SERVERS = "false"
  $env:E2E_BASE_URL = $frontendUrl
  & $npx playwright test @args
  $exitCode = $LASTEXITCODE
} finally {
  if ($frontend -and -not $frontend.HasExited) {
    Stop-Process -Id $frontend.Id -Force
  }
  if ($backend -and -not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force
  }
  if ($removeE2eDatabase -and (Test-Path $e2eDatabasePath)) {
    Remove-Item -LiteralPath $e2eDatabasePath -Force -ErrorAction SilentlyContinue
  }
}

exit $exitCode
