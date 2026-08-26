$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host '================================================'
Write-Host '  Tender Intelligence - Local Windows Launcher'
Write-Host '================================================'
Write-Host ''

function Get-PythonVersion {
    param([string[]]$CommandParts)
    try {
        $exe = $CommandParts[0]
        $args = @()
        if ($CommandParts.Count -gt 1) { $args = $CommandParts[1..($CommandParts.Count-1)] }
        $out = & $exe @args -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        return (($out | Select-Object -Last 1).ToString().Trim())
    } catch { return $null }
}

function Test-SupportedPythonVersion {
    param([string]$Version)
    return ($Version -eq '3.12' -or $Version -eq '3.11')
}

$candidates = @(
    @('py','-3.12'),
    @('py','-3.11'),
    @('python'),
    @('python3')
)

$pythonCmd = $null
$pythonVersion = $null
foreach ($candidate in $candidates) {
    $candidateVersion = Get-PythonVersion $candidate
    if (Test-SupportedPythonVersion $candidateVersion) {
        $pythonCmd = $candidate
        $pythonVersion = $candidateVersion
        break
    }
}

if (-not $pythonCmd) {
    Write-Host '[ERROR] Python 3.11 or 3.12 is required.' -ForegroundColor Red
    Write-Host 'Python 3.14 is not accepted for this project launcher.'
    Write-Host ''
    Write-Host 'Install Python 3.12 (64-bit), then run RUN_LOCAL_WINDOWS.bat again.'
    Write-Host 'During installation enable: Add python.exe to PATH.'
    Write-Host ''
    Read-Host 'Press Enter to close'
    exit 1
}

$pythonLabel = ($pythonCmd -join ' ')
Write-Host "[OK] Using Python: $pythonLabel ($pythonVersion)"

$venvPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $venvVersion = Get-PythonVersion @($venvPython)
    if (-not (Test-SupportedPythonVersion $venvVersion)) {
        Write-Host "[1/4] Existing virtual environment uses unsupported Python $venvVersion. Recreating it..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force '.venv'
    } else {
        Write-Host "[1/4] Virtual environment already exists (Python $venvVersion)."
    }
}

if (-not (Test-Path $venvPython)) {
    Write-Host '[1/4] Creating Python virtual environment...'
    $exe = $pythonCmd[0]
    $args = @()
    if ($pythonCmd.Count -gt 1) { $args = $pythonCmd[1..($pythonCmd.Count-1)] }
    & $exe @args -m venv .venv
}

if (-not (Test-Path $venvPython)) { throw 'Virtual environment creation failed.' }

Write-Host '[2/4] Checking/installing requirements...'
& $venvPython -m pip install --disable-pip-version-check -r requirements.txt

if (-not (Test-Path '.env')) {
    Write-Host '[3/4] Creating local .env from .env.example...'
    Copy-Item '.env.example' '.env'
} else {
    Write-Host '[3/4] Existing .env preserved.'
}

New-Item -ItemType Directory -Force -Path 'backups' | Out-Null

Write-Host '[4/4] Starting Tender Intelligence...'
$workDir = (Get-Location).Path
$serverCmd = "Set-Location '$($workDir.Replace("'","''"))'; & '$($venvPython.Replace("'","''"))' -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
Start-Process powershell.exe -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-Command',$serverCmd -WindowStyle Normal

$healthy = $false
for ($i=0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://127.0.0.1:8000/api/v1/health'
        if ($r.StatusCode -eq 200) { $healthy = $true; break }
    } catch {}
}

if (-not $healthy) {
    Write-Host '[WARNING] Server did not become healthy within 40 seconds.' -ForegroundColor Yellow
    Write-Host 'Check the Tender Intelligence server window and send the error to ChatGPT.'
    Read-Host 'Press Enter to close'
    exit 1
}

Start-Process 'http://127.0.0.1:8000'
Write-Host '[OK] Tender Intelligence is running locally.' -ForegroundColor Green
Write-Host 'Local URL: http://127.0.0.1:8000'
Write-Host 'Discovery: http://127.0.0.1:8000/discovery'
Write-Host 'Sources:   http://127.0.0.1:8000/sources'
