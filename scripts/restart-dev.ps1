param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 8001,
  [string]$HostName = "0.0.0.0",
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $RepoRoot "web\admin"
$LogRoot = Join-Path $RepoRoot ".tmp"
$BackendPidFile = Join-Path $LogRoot "backend-uvicorn.pid"
$FrontendPidFile = Join-Path $LogRoot "frontend-vite.pid"

if (-not (Test-Path $LogRoot)) {
  New-Item -ItemType Directory -Path $LogRoot | Out-Null
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
    Write-Warning "Backend did not listen on port $BackendPort within 30s. Check $errLog"
  } else {
    Set-Content -Path $BackendPidFile -Value $proc.Id
    Write-Host "Backend ready on port $BackendPort (listener PID: $($pids -join ', '), starter PID: $($proc.Id))"
  }
}

function Start-Frontend {
  $outLog = Join-Path $LogRoot "frontend-vite.out.log"
  $errLog = Join-Path $LogRoot "frontend-vite.err.log"
  $npm = (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)
  if (-not $npm) {
    $npm = Get-Command "npm" -ErrorAction Stop
  }

  Write-Host "Starting frontend: http://$HostName`:$FrontendPort"
  $proc = Start-Process `
    -FilePath $npm.Source `
    -ArgumentList @("run", "dev") `
    -WorkingDirectory $FrontendRoot `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -WindowStyle Hidden `
    -PassThru

  $pids = @(Wait-Port -Port $FrontendPort -TimeoutSeconds 45)
  if ($pids.Count -eq 0) {
    Write-Warning "Frontend did not listen on port $FrontendPort within 45s. Check $errLog"
  } else {
    Set-Content -Path $FrontendPidFile -Value $proc.Id
    Write-Host "Frontend ready on port $FrontendPort (listener PID: $($pids -join ', '), starter PID: $($proc.Id))"
  }
}

Write-Host "Restarting fp-agent dev services..."
Stop-PidFile -Path $FrontendPidFile
Stop-PidFile -Path $BackendPidFile
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
Start-Frontend
Write-Host ""
Write-Host "Done."
Write-Host "Backend docs: http://$HostName`:$BackendPort/docs"
Write-Host "Frontend:     http://$HostName`:$FrontendPort"
Write-Host "Logs:         $LogRoot"
