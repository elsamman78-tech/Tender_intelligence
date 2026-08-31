@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Tender Intelligence - Discovery Helpers

echo ================================================
echo   Tender Intelligence - Discovery Helpers
echo ================================================
echo.
where docker >nul 2>&1 || (
  echo [ERROR] Docker Desktop was not found.
  pause
  exit /b 1
)

docker info >nul 2>&1 || (
  echo [ERROR] Docker is installed but the Docker engine is not running.
  pause
  exit /b 1
)

echo [1/3] Starting SearXNG + ChangeDetection + RSS-Bridge...
docker compose -f "searxng\docker-compose.yml" up -d || goto :fail

echo [2/3] Waiting for SearXNG JSON search API...
powershell -NoProfile -Command "$ok=$false; 1..60 | ForEach-Object { try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 'http://127.0.0.1:8888/search?q=tender&format=json'; if($r.StatusCode -eq 200){$ok=$true; break} } catch {}; Start-Sleep -Seconds 2 }; if($ok){exit 0}else{exit 1}"
if errorlevel 1 (
  echo [ERROR] SearXNG did not become ready. Run: docker logs tender-searxng
  pause
  exit /b 1
)

echo [3/3] Enabling helper URLs in Tender Intelligence .env...
if not exist ".env" copy /Y ".env.example" ".env" >nul
powershell -NoProfile -Command "$p='.env'; $c=Get-Content $p -Raw; $pairs=@{'SEARXNG_URL'='http://127.0.0.1:8888';'CHANGEDETECTION_URL'='http://127.0.0.1:5000';'RSS_BRIDGE_URL'='http://127.0.0.1:3000'}; foreach($k in $pairs.Keys){$v=$pairs[$k]; if($c -match ('(?m)^'+[regex]::Escape($k)+'=.*$')){$c=[regex]::Replace($c,'(?m)^'+[regex]::Escape($k)+'.*$',$k+'='+$v)}else{$c=$c.TrimEnd()+[Environment]::NewLine+$k+'='+$v+[Environment]::NewLine}}; Set-Content -Path $p -Value $c -Encoding ascii"

echo.
echo [OK] SearXNG:        http://127.0.0.1:8888
echo [OK] ChangeDetection: http://127.0.0.1:5000
echo [OK] RSS-Bridge:      http://127.0.0.1:3000
echo Restart Tender Intelligence so it reloads .env.
start "" "http://127.0.0.1:8888"
pause
exit /b 0

:fail
echo [ERROR] Could not start discovery helpers.
pause
exit /b 1
