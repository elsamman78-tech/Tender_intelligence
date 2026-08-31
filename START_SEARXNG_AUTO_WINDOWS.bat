@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where docker >nul 2>&1 || (
  echo [INFO] Docker not found. SearXNG disabled; public Bing/DDG fallback will be used.
  exit /b 0
)

docker info >nul 2>&1 || (
  echo [INFO] Docker Desktop is installed but not running. SearXNG disabled; public Bing/DDG fallback will be used.
  exit /b 0
)

echo [SearXNG] Starting local metasearch with Docker...
docker compose -f "searxng\docker-compose.yml" up -d >nul 2>&1
if errorlevel 1 (
  echo [WARNING] Could not start SearXNG. Continuing with Bing/DDG fallback.
  exit /b 0
)

powershell -NoProfile -Command "$ok=$false; 1..30 | ForEach-Object { try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://127.0.0.1:8888/search?q=engineering+tender&format=json'; if($r.StatusCode -eq 200){$ok=$true; break} } catch {}; Start-Sleep -Seconds 1 }; if($ok){exit 0}else{exit 1}"
if errorlevel 1 (
  echo [WARNING] SearXNG container started but JSON API is not ready. Continuing with Bing/DDG fallback.
  exit /b 0
)

if not exist ".env" copy /Y ".env.example" ".env" >nul
powershell -NoProfile -Command "$p='.env'; $c=Get-Content $p -Raw; if($c -match '(?m)^SEARXNG_URL=.*$'){ $c=[regex]::Replace($c,'(?m)^SEARXNG_URL=.*$','SEARXNG_URL=http://127.0.0.1:8888') } else { $c=$c.TrimEnd()+[Environment]::NewLine+'SEARXNG_URL=http://127.0.0.1:8888'+[Environment]::NewLine }; Set-Content -Path $p -Value $c -Encoding ascii"

echo [OK] SearXNG ready: Google + Bing + Meta enabled through http://127.0.0.1:8888
exit /b 0
