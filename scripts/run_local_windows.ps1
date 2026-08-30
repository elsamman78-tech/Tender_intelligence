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
    return ($Version -in @('3.14','3.13','3.12','3.11'))
}

$candidates = @(
    @('py','-3.14'),
    @('py','-3.13'),
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
    Write-Host '[ERROR] Python 3.11, 3.12, 3.13 or 3.14 is required.' -ForegroundColor Red
    Write-Host 'Install a supported 64-bit Python version and enable Add python.exe to PATH.'
    Write-Host ''
    Read-Host 'Press Enter to close'
    exit 1
}

$pythonLabel = ($pythonCmd -join ' ')
Write-Host "[OK] Using Python: $pythonLabel ($pythonVersion)" -ForegroundColor Green

$venvPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $venvVersion = Get-PythonVersion @($venvPython)
    if (-not (Test-SupportedPythonVersion $venvVersion)) {
        Write-Host "[1/4] Existing virtual environment uses unsupported Python $venvVersion. Recreating it..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force '.venv'
    } elseif ($venvVersion -ne $pythonVersion) {
        Write-Host "[1/4] Existing virtual environment uses Python $venvVersion, detected Python is $pythonVersion. Recreating it..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force '.venv'
    } else {
        Write-Host "[1/4] Virtual environment already exists (Python $venvVersion)."
    }
}

if (-not (Test-Path $venvPython)) {
    Write-Host "[1/4] Creating Python $pythonVersion virtual environment..."
    $exe = $pythonCmd[0]
    $args = @()
    if ($pythonCmd.Count -gt 1) { $args = $pythonCmd[1..($pythonCmd.Count-1)] }
    & $exe @args -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}

if (-not (Test-Path $venvPython)) { throw 'Virtual environment creation failed.' }

Write-Host '[2/4] Upgrading pip and checking/installing requirements...'
& $venvPython -m pip install --disable-pip-version-check --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
& $venvPython -m pip install --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host '[ERROR] A dependency failed to install for this Python version.' -ForegroundColor Red
    Write-Host 'Copy the error shown above and send it to ChatGPT.'
    Read-Host 'Press Enter to close'
    exit 1
}

# JavaScript-heavy procurement portals (Etimad, ESNAD, etc.) use Playwright/Crawlee.
# Install Chromium once per virtual environment. Failure is non-fatal because the
# connector layer has an HTTP fallback and the evaluation report exposes source health.
$browserMarker = Join-Path (Get-Location) '.venv\.tender_playwright_chromium_ready'
if (-not (Test-Path $browserMarker)) {
    Write-Host '[2b/4] Preparing Chromium for JavaScript tender portals (one-time setup)...'
    & $venvPython -m playwright install chromium
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $browserMarker -Value (Get-Date).ToString('o')
        Write-Host '[OK] JavaScript portal browser is ready.' -ForegroundColor Green
    } else {
        Write-Host '[WARNING] Chromium setup failed. Static connectors will still work; JS portals will use HTTP fallback.' -ForegroundColor Yellow
    }
} else {
    Write-Host '[2b/4] JavaScript portal browser already prepared.'
}

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
for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://127.0.0.1:8000/api/v1/health'
        if ($r.StatusCode -eq 200) { $healthy = $true; break }
    } catch {}
}

if (-not $healthy) {
    Write-Host '[WARNING] Server did not become healthy within 60 seconds.' -ForegroundColor Yellow
    Write-Host 'Check the Tender Intelligence server window and send the error to ChatGPT.'
    Read-Host 'Press Enter to close'
    exit 1
}

Start-Process 'http://127.0.0.1:8000'
Write-Host '[OK] Tender Intelligence is running locally.' -ForegroundColor Green
Write-Host 'Local URL: http://127.0.0.1:8000'
Write-Host 'Discovery: http://127.0.0.1:8000/discovery'
Write-Host 'Sources:   http://127.0.0.1:8000/sources'
