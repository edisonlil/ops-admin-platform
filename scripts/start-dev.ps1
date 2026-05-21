param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 8001,
  [string]$HostName = "0.0.0.0",
  [string]$Python = "python",
  [switch]$NonInteractive,
  [switch]$SkipBuild,
  [switch]$SkipInstall,
  [switch]$InitializeStorage
)

$ErrorActionPreference = "Stop"

function Normalize-ProcessPathEnvironment {
  $pathValue = [Environment]::GetEnvironmentVariable("Path", "Process")
  if ([string]::IsNullOrWhiteSpace($pathValue)) {
    $pathValue = [Environment]::GetEnvironmentVariable("PATH", "Process")
  }
  if (-not [string]::IsNullOrWhiteSpace($pathValue)) {
    [Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
    [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
  }
}

Normalize-ProcessPathEnvironment

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $RepoRoot "web\admin"
$ConfigRoot = Join-Path $RepoRoot "config"
$ApplicationConfigPath = Join-Path $ConfigRoot "application.local.json"
$LegacyDatabaseConfigPath = Join-Path $ConfigRoot "database.local.json"
$FrontendEnvPath = Join-Path $FrontendRoot ".env.development.local"
$LogRoot = Join-Path $RepoRoot ".tmp"
$BackendPidFile = Join-Path $LogRoot "backend-uvicorn.pid"
$FrontendPidFile = Join-Path $LogRoot "frontend-vite.pid"
$CronWorkerPidFile = Join-Path $LogRoot "cron-worker.pid"

if (-not (Test-Path $LogRoot)) {
  New-Item -ItemType Directory -Path $LogRoot | Out-Null
}
if (-not (Test-Path $ConfigRoot)) {
  New-Item -ItemType Directory -Path $ConfigRoot | Out-Null
}

function Read-Default {
  param(
    [string]$Prompt,
    [string]$Default
  )

  if ($NonInteractive) {
    return $Default
  }

  $suffix = if ([string]::IsNullOrWhiteSpace($Default)) { "" } else { " [$Default]" }
  $value = Read-Host "$Prompt$suffix"
  if ([string]::IsNullOrWhiteSpace($value)) {
    return $Default
  }
  return $value.Trim()
}

function Read-Port {
  param(
    [string]$Prompt,
    [int]$Default
  )

  while ($true) {
    $raw = Read-Default -Prompt $Prompt -Default ([string]$Default)
    $port = 0
    if ([int]::TryParse($raw, [ref]$port) -and $port -ge 1 -and $port -le 65535) {
      return $port
    }
    Write-Host "Please enter a valid port from 1 to 65535."
  }
}

function Read-Choice {
  param(
    [string]$Prompt,
    [string]$Default,
    [string[]]$Choices
  )

  while ($true) {
    $value = (Read-Default -Prompt $Prompt -Default $Default).ToLowerInvariant()
    if ($Choices -contains $value) {
      return $value
    }
    Write-Host "Please enter one of: $($Choices -join ', ')."
  }
}

function Load-JsonConfig {
  param([string]$Path)

  if (-not (Test-Path $Path)) {
    return @{}
  }
  $raw = Get-Content -Path $Path -Raw -Encoding UTF8
  if ([string]::IsNullOrWhiteSpace($raw)) {
    return @{}
  }
  $parsed = ConvertFrom-Json -InputObject $raw
  $result = @{}
  foreach ($property in $parsed.PSObject.Properties) {
    $result[$property.Name] = $property.Value
  }
  return $result
}

function Load-DatabaseConfig {
  $application = Load-JsonConfig -Path $ApplicationConfigPath
  if ($application.ContainsKey("database") -and $null -ne $application.database) {
    $database = @{}
    foreach ($property in $application.database.PSObject.Properties) {
      $database[$property.Name] = $property.Value
    }
    return $database
  }
  return Load-JsonConfig -Path $LegacyDatabaseConfigPath
}

function Config-Value {
  param(
    [hashtable]$Config,
    [string]$Name,
    [string]$Fallback = ""
  )

  if ($Config.ContainsKey($Name) -and $null -ne $Config[$Name]) {
    return [string]$Config[$Name]
  }
  return $Fallback
}

function Save-Json {
  param(
    [string]$Path,
    [hashtable]$Payload
  )

  $json = $Payload | ConvertTo-Json -Depth 6
  Write-Utf8NoBom -Path $Path -Lines @($json)
}

function Save-ApplicationDatabaseConfig {
  $database = @{
    backend = $script:Backend
  }
  if ($script:Backend -eq "mysql" -or $script:Backend -eq "postgres") {
    $database.database_url = $script:DatabaseUrl
  } else {
    $database.sqlite_path = $script:SqlitePath
  }

  $application = Load-JsonConfig -Path $ApplicationConfigPath
  $application.database = $database
  Save-Json -Path $ApplicationConfigPath -Payload $application
  Write-Host "Application config updated: $ApplicationConfigPath"
}

function Write-Utf8NoBom {
  param(
    [string]$Path,
    [string[]]$Lines
  )

  $encoding = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllLines($Path, $Lines, $encoding)
}

function Configure-PortsAndDatabase {
  if (-not $NonInteractive) {
    $script:BackendPort = Read-Port -Prompt "Backend port" -Default $BackendPort
    $script:FrontendPort = Read-Port -Prompt "Frontend port" -Default $FrontendPort
    if ($script:BackendPort -eq $script:FrontendPort) {
      throw "Backend and frontend ports must be different."
    }
  } else {
    # In non-interactive mode, use default ports if not provided via args
    Write-Host "Using default ports: Backend=$BackendPort, Frontend=$FrontendPort"
  }

  # Check if database config already exists
  $existing = Load-DatabaseConfig
  if ($existing -and $existing.backend) {
    # Use existing config
    Write-Host "Using existing database config: $($existing.backend)"
    $script:Backend = $existing.backend
    if ($script:Backend -eq "mysql" -or $script:Backend -eq "postgres") {
      $script:DatabaseUrl = $existing.database_url
    } else {
      $script:SqlitePath = $existing.sqlite_path
    }
  } else {
    # No existing config, this shouldn't happen if setup was run
    if ($NonInteractive) {
      Write-Host "Warning: No database config found. Please run 'ops-cli setup' first."
      # Default to sqlite
      $script:Backend = "sqlite"
      $script:SqlitePath = "ops_admin.db"
    } else {
      $defaultBackend = $existingBackend = Config-Value -Config $existing -Name "backend"
      if (-not $defaultBackend) {
        $defaultBackend = "sqlite"
      }
      $backend = Read-Choice -Prompt "Database backend (sqlite/mysql/postgres)" -Default $defaultBackend -Choices @("sqlite", "mysql", "postgres")

      $script:Backend = $backend

      if ($backend -eq "postgres" -or $backend -eq "mysql") {
        $defaultUrl = Config-Value -Config $existing -Name "database_url"
        $databaseUrl = Read-Default -Prompt "Database URL" -Default $defaultUrl
        if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
          throw "Database URL is required when database backend is $backend."
        }
        $script:DatabaseUrl = $databaseUrl
      } else {
        $defaultPath = Config-Value -Config $existing -Name "sqlite_path"
        if ([string]::IsNullOrWhiteSpace($defaultPath)) {
          $defaultPath = Config-Value -Config $existing -Name "db_path" -Fallback "ops_admin.db"
        }
        $sqlitePath = Read-Default -Prompt "SQLite database path" -Default $defaultPath
        if ([string]::IsNullOrWhiteSpace($sqlitePath)) {
          $sqlitePath = "ops_admin.db"
        }
        $script:SqlitePath = $sqlitePath
      }
    }
  }

  Save-ApplicationDatabaseConfig

  # Set environment variables
  $env:OPS_ADMIN_APPLICATION_CONFIG = $ApplicationConfigPath
  $env:FG_AGENT_CORS_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
}

function Configure-PythonPath {
  $localPaths = @(
    $RepoRoot,
    (Join-Path $RepoRoot "packages\python\ops-admin-system\src"),
    (Join-Path $RepoRoot "packages\python\ops-admin-identity-access\src"),
    (Join-Path $RepoRoot "packages\python\ops-admin-messaging\src"),
    (Join-Path $RepoRoot "packages\python\ops-admin-appearance\src"),
    (Join-Path $RepoRoot "packages\python\ops-admin-llm-runtime\src")
  )
  $existingPaths = @()
  if (-not [string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $existingPaths = @($env:PYTHONPATH -split [regex]::Escape([System.IO.Path]::PathSeparator))
  }
  $env:PYTHONPATH = (($localPaths + $existingPaths) | Where-Object {
    -not [string]::IsNullOrWhiteSpace($_)
  } | Select-Object -Unique) -join [System.IO.Path]::PathSeparator
}

function Set-EnvValue {
  param(
    [string[]]$Lines,
    [string]$Name,
    [string]$Value
  )

  $replacement = "$Name = $Value"
  $found = $false
  $updated = @(foreach ($line in $Lines) {
    if ($line -match "^\s*$([regex]::Escape($Name))\s*=") {
      $found = $true
      $replacement
    } else {
      $line
    }
  })
  if (-not $found) {
    $updated = @($updated) + $replacement
  }
  return $updated
}

function Update-FrontendEnv {
  $lines = @(
    "# Generated by scripts/start-dev.ps1. This file is local-only."
  )
  $lines = Set-EnvValue -Lines $lines -Name "VITE_PORT" -Value ([string]$FrontendPort)
  $proxyValue = "[[`"/api`",`"http://127.0.0.1:$BackendPort/api`"]]"
  $lines = Set-EnvValue -Lines $lines -Name "VITE_PROXY" -Value $proxyValue
  Write-Utf8NoBom -Path $FrontendEnvPath -Lines $lines
  Write-Host "Frontend dev env updated: $FrontendEnvPath"
}

function Invoke-Checked {
  param(
    [string]$FilePath,
    [string[]]$ArgumentList,
    [string]$WorkingDirectory,
    [string]$Label
  )

  Write-Host $Label
  Push-Location $WorkingDirectory
  try {
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
      throw "$Label failed with exit code $LASTEXITCODE."
    }
  } finally {
    Pop-Location
  }
}

function Ensure-BackendReady {
  if ($SkipInstall) {
    return
  }

  $probe = @"
import importlib.util
missing = [
    name
    for name in (
        "fastapi",
        "uvicorn",
        "pydantic",
        "sqlalchemy",
        "system",
        "identity_access",
        "appearance",
        "llm_runtime",
        "ai_applications",
        "ai_capabilities",
    )
    if importlib.util.find_spec(name) is None
]
raise SystemExit(1 if missing else 0)
"@
  $probeResult = & $Python -c $probe
  if ($LASTEXITCODE -eq 0) {
    return
  }

  Invoke-Checked `
    -FilePath $Python `
    -ArgumentList @("-m", "pip", "install", "-r", "requirements.txt") `
    -WorkingDirectory $RepoRoot `
    -Label "Installing backend dependencies..."
}

function PackageManager {
  $pnpm = Get-Command "pnpm.cmd" -ErrorAction SilentlyContinue
  if (-not $pnpm) {
    $pnpm = Get-Command "pnpm" -ErrorAction SilentlyContinue
  }
  if ($pnpm) {
    return @{
      File = $pnpm.Source
      Install = @("install")
      Dev = @("run", "dev")
      Build = @("run", "build")
    }
  }

  $npm = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
  if (-not $npm) {
    $npm = Get-Command "npm" -ErrorAction SilentlyContinue
  }
  if (-not $npm) {
    throw "Node package manager not found. Install pnpm or npm, then retry."
  }
  return @{
    File = $npm.Source
    Install = @("install")
    Dev = @("run", "dev")
    Build = @("run", "build")
  }
}

function Ensure-FrontendReady {
  $pm = PackageManager
  $nodeModulesPath = Join-Path $FrontendRoot "node_modules"
  if (-not $SkipInstall -and -not (Test-Path $nodeModulesPath)) {
    Invoke-Checked `
      -FilePath $pm.File `
      -ArgumentList $pm.Install `
      -WorkingDirectory $FrontendRoot `
      -Label "Installing frontend dependencies..."
  }

  $distIndex = Join-Path $FrontendRoot "dist\index.html"
  if (-not $SkipBuild -and -not (Test-Path $distIndex)) {
    Invoke-Checked `
      -FilePath $pm.File `
      -ArgumentList $pm.Build `
      -WorkingDirectory $FrontendRoot `
      -Label "Building frontend because dist is missing..."
  }
}

function Initialize-DatabaseStorage {
  if (-not $InitializeStorage) {
    $answer = Read-Choice -Prompt "Initialize or update database schema now? (y/n)" -Default "n" -Choices @("y", "n")
    if ($answer -ne "y") {
      return
    }
  }

  foreach ($scriptName in @("init_identity_access.py", "init_personalization.py", "init_messaging.py", "init_appearance.py", "init_llm_runtime.py", "init_cron.py", "init_ai_applications.py", "init_ai_capabilities.py")) {
    Invoke-Checked `
      -FilePath $Python `
      -ArgumentList @((Join-Path "scripts" $scriptName)) `
      -WorkingDirectory $RepoRoot `
      -Label "Running $scriptName..."
  }
}

function Get-ListeningPids {
  param([int]$Port)

  $lines = netstat -ano | Select-String -Pattern "LISTENING\s+(\d+)$" | Where-Object {
    $_.Line -match "[:\.]$Port\s+"
  }

  $lines | ForEach-Object {
    if ($_.Line -match "LISTENING\s+(\d+)$") {
      [int]$Matches[1]
    }
  } | Sort-Object -Unique
}

function Get-ProcessTreePids {
  param([int[]]$RootPids)

  $allProcesses = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
  $seen = @{}
  $queue = [System.Collections.Generic.Queue[int]]::new()

  foreach ($processId in $RootPids) {
    if ($processId -gt 0 -and -not $seen.ContainsKey($processId)) {
      $seen[$processId] = $true
      $queue.Enqueue($processId)
    }
  }

  while ($queue.Count -gt 0) {
    $parentId = $queue.Dequeue()
    foreach ($child in @($allProcesses | Where-Object { $_.ParentProcessId -eq $parentId })) {
      $childId = [int]$child.ProcessId
      if (-not $seen.ContainsKey($childId)) {
        $seen[$childId] = $true
        $queue.Enqueue($childId)
      }
    }
  }

  $seen.Keys | ForEach-Object { [int]$_ }
}

function Stop-ProcessTree {
  param(
    [int[]]$ProcessIds,
    [string]$Label
  )

  $treePids = @(Get-ProcessTreePids -RootPids $ProcessIds)
  if ($treePids.Count -eq 0) {
    return
  }

  foreach ($processId in @($treePids | Sort-Object -Descending)) {
    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "$Label stopping PID $processId ($($proc.ProcessName))"
      Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
  }
}

function Stop-Port {
  param([int]$Port)

  $pids = @(Get-ListeningPids -Port $Port)
  if ($pids.Count -eq 0) {
    Write-Host "Port ${Port}: no listener"
    return
  }

  Stop-ProcessTree -ProcessIds $pids -Label "Port ${Port}:"
}

function Stop-PidFile {
  param([string]$Path)

  if (-not (Test-Path $Path)) {
    return
  }

  $processIds = @(Get-Content $Path -ErrorAction SilentlyContinue | Where-Object { $_ -match "^\d+$" })
  $existingProcessIds = @()
  foreach ($processId in $processIds) {
    if (Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue) {
      $existingProcessIds += [int]$processId
    }
  }

  if ($existingProcessIds.Count -gt 0) {
    Stop-ProcessTree -ProcessIds $existingProcessIds -Label "Previous starter:"
  }

  Remove-Item $Path -Force -ErrorAction SilentlyContinue
}

function Wait-Port-Free {
  param(
    [int]$Port,
    [int]$TimeoutSeconds = 15
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    $pids = @(Get-ListeningPids -Port $Port)
    if ($pids.Count -eq 0) {
      return $true
    }
    Stop-ProcessTree -ProcessIds $pids -Label "Port ${Port}:"
    Start-Sleep -Milliseconds 500
  }

  return $false
}

function Wait-Port {
  param(
    [int]$Port,
    [int]$TimeoutSeconds = 30
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    $pids = @(Get-ListeningPids -Port $Port)
    if ($pids.Count -gt 0) {
      return $pids
    }
    Start-Sleep -Milliseconds 500
  }

  return @()
}

function Start-Backend {
  $outLog = Join-Path $LogRoot "backend-uvicorn.out.log"
  $errLog = Join-Path $LogRoot "backend-uvicorn.err.log"

  Write-Host "Starting backend: http://$HostName`:$BackendPort"
  $proc = Start-Process `
    -FilePath $Python `
    -ArgumentList @("-m", "uvicorn", "api.main:app", "--host", $HostName, "--port", "$BackendPort", "--reload") `
    -WorkingDirectory $RepoRoot `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -WindowStyle Hidden `
    -PassThru

  $pids = @(Wait-Port -Port $BackendPort -TimeoutSeconds 30)
  if ($pids.Count -eq 0) {
    Stop-ProcessTree -ProcessIds @($proc.Id) -Label "Backend startup failed:"
    throw "Backend did not listen on port $BackendPort within 30s. Check $errLog"
  } else {
    Set-Content -Path $BackendPidFile -Value $proc.Id
    Write-Host "Backend ready on port $BackendPort (listener PID: $($pids -join ', '), starter PID: $($proc.Id))"
  }
}

function Start-Frontend {
  $outLog = Join-Path $LogRoot "frontend-vite.out.log"
  $errLog = Join-Path $LogRoot "frontend-vite.err.log"
  $pm = PackageManager

  Write-Host "Starting frontend: http://$HostName`:$FrontendPort"
  $proc = Start-Process `
    -FilePath $pm.File `
    -ArgumentList $pm.Dev `
    -WorkingDirectory $FrontendRoot `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -WindowStyle Hidden `
    -PassThru

  $pids = @(Wait-Port -Port $FrontendPort -TimeoutSeconds 45)
  if ($pids.Count -eq 0) {
    Stop-ProcessTree -ProcessIds @($proc.Id) -Label "Frontend startup failed:"
    throw "Frontend did not listen on port $FrontendPort within 45s. Check $errLog"
  } else {
    Set-Content -Path $FrontendPidFile -Value $proc.Id
    Write-Host "Frontend ready on port $FrontendPort (listener PID: $($pids -join ', '), starter PID: $($proc.Id))"
  }
}

function Start-CronWorker {
  $outLog = Join-Path $LogRoot "cron-worker.out.log"
  $errLog = Join-Path $LogRoot "cron-worker.err.log"

  Write-Host "Starting cron worker"
  $proc = Start-Process `
    -FilePath $Python `
    -ArgumentList @((Join-Path "scripts" "run_cron_worker.py")) `
    -WorkingDirectory $RepoRoot `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -WindowStyle Hidden `
    -PassThru

  Start-Sleep -Seconds 2
  if (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue) {
    Set-Content -Path $CronWorkerPidFile -Value $proc.Id
    Write-Host "Cron worker started (PID: $($proc.Id))"
  } else {
    throw "Cron worker exited during startup. Check $errLog"
  }
}

Write-Host "Starting ops-admin-platform dev services..."
Configure-PortsAndDatabase
Configure-PythonPath
Update-FrontendEnv
Ensure-BackendReady
Ensure-FrontendReady
Initialize-DatabaseStorage

Stop-PidFile -Path $FrontendPidFile
Stop-PidFile -Path $BackendPidFile
Stop-PidFile -Path $CronWorkerPidFile
Stop-Port -Port $FrontendPort
Stop-Port -Port $BackendPort
$portsReleased = $true
if (-not (Wait-Port-Free -Port $FrontendPort -TimeoutSeconds 15)) {
  Write-Warning "Port $FrontendPort is still in use after stopping old frontend processes."
  $portsReleased = $false
}
if (-not (Wait-Port-Free -Port $BackendPort -TimeoutSeconds 15)) {
  Write-Warning "Port $BackendPort is still in use after stopping old backend processes."
  $portsReleased = $false
}
if (-not $portsReleased) {
  throw "One or more target ports are still occupied. Run this script from an elevated terminal, or close the listed processes and retry."
}

Start-Backend
Start-CronWorker
Start-Frontend
Write-Host ""
Write-Host "Done."
Write-Host "Backend docs: http://127.0.0.1:$BackendPort/docs"
Write-Host "Frontend:     http://127.0.0.1:$FrontendPort"
Write-Host "Cron worker:  started"
Write-Host "Logs:         $LogRoot"
