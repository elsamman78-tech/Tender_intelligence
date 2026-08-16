@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Tender Intelligence - SearXNG

echo ================================================
echo   Tender Intelligence - Local SearXNG
echo ================================================
echo.
where docker >nul 2>&1 || (
  echo [ERROR] Docker Desktop was not found.
  echo Install/start Docker Desktop, then run this file again.
  pause
  exit /b 1
)

docker info >nul 2>&1 || (
  echo [ERROR] Docker is installed but the Docker engine is not running.
  echo Start Docker Desktop and wait until it is ready.
  pause
  exit /b 1
)

echo [1/3] Starting SearXNG...
docker compose -f "searxng\docker-compose.yml" up -d || goto :fail

echo [2/3] Waiting for JSON search API...
powershell -NoProfile -Command "$ok=$false; 1..60 | ForEach-Object { try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 'http://127.0.0.1:8888/search?q=tender&format=json'; if($r.StatusCode -eq 200){$ok=$true; break} } catch {}; Start-Sleep -Seconds 2 }; if($ok){exit 0}else{exit 1}"
if errorlevel 1 (
  echo [ERROR] SearXNG did not become ready. Run: docker logs tender-searxng
  pause
  exit /b 1
)

echo [3/3] Enabling SearXNG in Tender Intelligence .env...
if not exist ".env" copy /Y ".env.example" ".env" >nul
powershell -NoProfile -Command "$p='.env'; $c=Get-Content $p -Raw; if($c -match '(?m)^SEARXNG_URL=.*$'){ $c=[regex]::Replace($c,'(?m)^SEARXNG_URL=.*$','SEARXNG_URL=http://127.0.0.1:8888') } else { $c=$c.TrimEnd()+[Environment]::NewLine+'SEARXNG_URL=http://127.0.0.1:8888'+[Environment]::NewLine }; Set-Content -Path $p -Value $c -Encoding ascii"

echo.
echo [OK] SearXNG is running on http://127.0.0.1:8888
echo Google, Bing and SearXNG Meta providers are now enabled.
echo Restart Tender Intelligence so it reloads .env.
start "" "http://127.0.0.1:8888"
pause
exit /b 0

:fail
echo [ERROR] Could not start SearXNG.
pause
exit /b 1
