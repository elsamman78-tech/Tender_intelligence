$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host '================================================'
Write-Host '  Tender Intelligence - Local Windows Launcher'
Write-Host '================================================'
Write-Host ''

function Get-PythonVersion {
    param([string[]]$CommandParts)
    try {
        $exe=$CommandParts[0]; $args=@()
        if ($CommandParts.Count -gt 1) { $args=$CommandParts[1..($CommandParts.Count-1)] }
        $out=& $exe @args -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        return (($out | Select-Object -Last 1).ToString().Trim())
    } catch { return $null }
}
function Test-SupportedPythonVersion { param([string]$Version); return ($Version -in @('3.14','3.13','3.12','3.11')) }
function Set-EnvValue {
    param([string]$Name,[string]$Value)
    $path='.env'; $content=Get-Content $path -Raw; $escaped=[regex]::Escape($Name)
    if ($content -match "(?m)^$escaped=.*$") { $content=[regex]::Replace($content,"(?m)^$escaped=.*$","$Name=$Value") }
    else { $content=$content.TrimEnd()+[Environment]::NewLine+"$Name=$Value"+[Environment]::NewLine }
    Set-Content -Path $path -Value $content -Encoding ascii
}

$candidates=@(@('py','-3.14'),@('py','-3.13'),@('py','-3.12'),@('py','-3.11'),@('python'),@('python3'))
$pythonCmd=$null; $pythonVersion=$null
foreach ($candidate in $candidates) {
    $candidateVersion=Get-PythonVersion $candidate
    if (Test-SupportedPythonVersion $candidateVersion) { $pythonCmd=$candidate; $pythonVersion=$candidateVersion; break }
}
if (-not $pythonCmd) {
    Write-Host '[ERROR] Python 3.11, 3.12, 3.13 or 3.14 is required.' -ForegroundColor Red
    Read-Host 'Press Enter to close'; exit 1
}
Write-Host "[OK] Using Python: $($pythonCmd -join ' ') ($pythonVersion)" -ForegroundColor Green

$venvPython=Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $venvVersion=Get-PythonVersion @($venvPython)
    if (-not (Test-SupportedPythonVersion $venvVersion) -or $venvVersion -ne $pythonVersion) {
        Write-Host "[1/5] Recreating virtual environment ($venvVersion -> $pythonVersion)..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force '.venv'
    } else { Write-Host "[1/5] Virtual environment already exists (Python $venvVersion)." }
}
if (-not (Test-Path $venvPython)) {
    Write-Host "[1/5] Creating Python $pythonVersion virtual environment..."
    $exe=$pythonCmd[0]; $args=@(); if ($pythonCmd.Count -gt 1) { $args=$pythonCmd[1..($pythonCmd.Count-1)] }
    & $exe @args -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}

Write-Host '[2/5] Installing/updating requirements...'
& $venvPython -m pip install --disable-pip-version-check --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
& $venvPython -m pip install --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { Read-Host 'Dependency install failed. Press Enter to close'; exit 1 }

$browserMarker=Join-Path (Get-Location) '.venv\.tender_playwright_chromium_ready'
if (-not (Test-Path $browserMarker)) {
    Write-Host '[2b/5] Preparing Chromium for JavaScript tender portals...'
    & $venvPython -m playwright install chromium
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $browserMarker -Value (Get-Date).ToString('o'); Write-Host '[OK] Chromium ready.' -ForegroundColor Green }
    else { Write-Host '[WARNING] Chromium setup failed; static fallback remains available.' -ForegroundColor Yellow }
} else { Write-Host '[2b/5] Chromium already prepared.' }

if (-not (Test-Path '.env')) { Write-Host '[3/5] Creating .env...'; Copy-Item '.env.example' '.env' }
else { Write-Host '[3/5] Existing .env preserved.' }

Write-Host '[4/5] Starting zero-cost discovery helpers when Docker is available...'
$dockerReady=$false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    try { docker info *> $null; if ($LASTEXITCODE -eq 0) { $dockerReady=$true } } catch {}
}
if ($dockerReady) {
    try {
        docker compose -f 'searxng\docker-compose.yml' up -d
        if ($LASTEXITCODE -eq 0) {
            $searxReady=$false
            for ($i=0; $i -lt 30; $i++) {
                try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://127.0.0.1:8888/search?q=tender&format=json'; if ($r.StatusCode -eq 200) { $searxReady=$true; break } } catch {}
                Start-Sleep -Seconds 1
            }
            if ($searxReady) { Set-EnvValue 'SEARXNG_URL' 'http://127.0.0.1:8888'; Write-Host '[OK] SearXNG enabled.' -ForegroundColor Green }
            try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 'http://127.0.0.1:5000/'; if ($r.StatusCode -ge 200) { Set-EnvValue 'CHANGEDETECTION_URL' 'http://127.0.0.1:5000'; Write-Host '[OK] ChangeDetection enabled.' -ForegroundColor Green } } catch {}
            try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 'http://127.0.0.1:3000/'; if ($r.StatusCode -ge 200) { Set-EnvValue 'RSS_BRIDGE_URL' 'http://127.0.0.1:3000'; Write-Host '[OK] RSS-Bridge enabled.' -ForegroundColor Green } } catch {}
        }
        docker image inspect tender-ocrmypdf:latest *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host '[4b/5] Building Arabic + English + French OCR image (one-time)...'
            docker compose -f 'searxng\docker-compose.yml' build ocr
        }
        docker image inspect tender-ocrmypdf:latest *> $null
        if ($LASTEXITCODE -eq 0) { Set-EnvValue 'OCR_DOCKER_IMAGE' 'tender-ocrmypdf:latest'; Write-Host '[OK] Multilingual scanned-PDF OCR ready.' -ForegroundColor Green }
    } catch { Write-Host '[INFO] Optional Docker helpers unavailable; native discovery continues.' -ForegroundColor Yellow }
} else { Write-Host '[INFO] Docker unavailable. Native discovery + Playwright will continue normally.' -ForegroundColor Yellow }

New-Item -ItemType Directory -Force -Path 'backups' | Out-Null
Write-Host '[5/5] Starting Tender Intelligence...'
$workDir=(Get-Location).Path
$serverCmd="Set-Location '$($workDir.Replace("'","''"))'; & '$($venvPython.Replace("'","''"))' -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
Start-Process powershell.exe -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-Command',$serverCmd -WindowStyle Normal

$healthy=$false
for ($i=0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 1
    try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 'http://127.0.0.1:8000/api/v1/health/live'; if ($r.StatusCode -eq 200) { $healthy=$true; break } } catch {}
}
if (-not $healthy) {
    Write-Host '[WARNING] Server started but liveness probe did not answer.' -ForegroundColor Yellow
    Read-Host 'Press Enter to close'; exit 1
}
Start-Process 'http://127.0.0.1:8000'
Write-Host '[OK] Tender Intelligence is running locally.' -ForegroundColor Green
Write-Host 'Local URL: http://127.0.0.1:8000'
Write-Host 'Discovery: http://127.0.0.1:8000/discovery'
Write-Host 'Sources:   http://127.0.0.1:8000/sources'
