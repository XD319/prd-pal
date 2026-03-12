param(
    [switch]$NoBrowser,
    [switch]$DryRun
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendUrl = 'http://127.0.0.1:5173/'
$backendLauncher = Join-Path $repoRoot 'start-backend-dev.cmd'
$frontendLauncher = Join-Path $repoRoot 'start-frontend-dev.cmd'

Write-Host "Repo root: $repoRoot"
Write-Host "Backend launcher: $backendLauncher"
Write-Host "Frontend launcher: $frontendLauncher"
Write-Host "Frontend URL: $frontendUrl"

if ($DryRun) {
    exit 0
}

Start-Process cmd.exe -ArgumentList @('/k', "`"$frontendLauncher`"") | Out-Null
if (-not $NoBrowser) {
    Start-Sleep -Seconds 5
    Start-Process $frontendUrl | Out-Null
}

& $backendLauncher
