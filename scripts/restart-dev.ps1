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
$StartScript = Join-Path $PSScriptRoot "start-dev.ps1"
& $StartScript `
  -BackendPort $BackendPort `
  -FrontendPort $FrontendPort `
  -HostName $HostName `
  -Python $Python `
  -NonInteractive:$NonInteractive `
  -SkipBuild:$SkipBuild `
  -SkipInstall:$SkipInstall `
  -InitializeStorage:$InitializeStorage
