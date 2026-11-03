<#
.SYNOPSIS
  Parametric Studio installer for Windows. UNTESTED ON WINDOWS: it was written and checked on Linux only and has never run on a Windows machine.
.DESCRIPTION
  Checks for Python 3.12, Git, ffmpeg and an NVIDIA or AMD driver, shows install.py's plan (a dry run that changes nothing), asks, then runs install.py,
  which sets up ComfyUI, the studio and the models in -Dir and writes run_studio.bat. If a step fails, please open an issue with its output.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1 -Goals anime
#>
[CmdletBinding()]
param(
    [string]$Goals = "image",
    [ValidateSet("stable", "nightly")][string]$Channel = "stable",
    [string]$Dir = "",
    [switch]$NoModels,
    [switch]$Yes
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "Parametric Studio installer for Windows. UNTESTED ON WINDOWS: it has only been checked on Linux." -ForegroundColor Yellow

$Repo = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Repo "install.py"))) { throw "Run this from the Parametric Studio folder: scripts\install_windows.ps1 (install.py was not found in $Repo)." }
if (-not $Dir) { $Dir = Join-Path (Split-Path -Parent $Repo) "parametric-studio-runtime" }

function Test-Tool([string]$Name, [string]$Hint) {
    if (Get-Command $Name -ErrorAction SilentlyContinue) { return $true }
    Write-Host "Missing: $Name. $Hint" -ForegroundColor Red
    return $false
}

$ok = $true
$py = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.12 -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) { $py = @("py", "-3.12") }
}
if (-not $py) {
    Write-Host "Missing: Python 3.12. Install it from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'." -ForegroundColor Red
    $ok = $false
}
$ok = (Test-Tool "git" "Install Git from https://git-scm.com/download/win.") -and $ok
$ok = (Test-Tool "ffmpeg" "Install ffmpeg (https://ffmpeg.org/download.html) and add its bin folder to PATH.") -and $ok
$ok = (Test-Tool "ffprobe" "It comes with ffmpeg; add ffmpeg's bin folder to PATH.") -and $ok
if (-not $ok) { exit 1 }

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
} else {
    Write-Host "nvidia-smi was not found. On NVIDIA, update the driver first; on AMD the planner uses ROCm and is less tried." -ForegroundColor Yellow
}

$longPaths = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -ErrorAction SilentlyContinue
if (-not $longPaths -or $longPaths.LongPathsEnabled -ne 1) {
    Write-Host "Long paths are off. Some Python packages have deep folders; if pip fails with a path error, turn on 'Enable Win32 long paths' and run this again." -ForegroundColor Yellow
}

$installArgs = @((Join-Path $Repo "install.py"), "--goals", $Goals, "--channel", $Channel, "--dir", $Dir)
if ($NoModels) { $installArgs += "--no-models" }

Write-Host "`nThe plan (a dry run: nothing is changed yet):"
& $py[0] $py[1] @installArgs --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $Yes) {
    $answer = Read-Host "`nInstall this? [y/N]"
    if ($answer -notmatch "^[yY]") { Write-Host "Stopped. Nothing was changed."; exit 0 }
}
& $py[0] $py[1] @installArgs --yes
if ($LASTEXITCODE -ne 0) {
    Write-Host "A step failed. Run the same command again: finished steps and partly downloaded files are kept." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "`nInstalled. Start it with: $(Join-Path $Dir 'run_studio.bat'), then open http://127.0.0.1:8310" -ForegroundColor Green
Write-Host "Windows may refuse the symlink for the custom nodes without Developer Mode; install.py then copies the folder instead."
