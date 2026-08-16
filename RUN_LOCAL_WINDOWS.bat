@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Tender Intelligence - Local Launcher

echo ================================================
echo   Tender Intelligence - Local Windows Launcher
echo ================================================
echo.

set "PY_CMD="
where py >nul 2>&1 && set "PY_CMD=py"
if not defined PY_CMD (
  where python >nul 2>&1 && set "PY_CMD=python"
)
if not defined PY_CMD (
  echo [ERROR] Python was not found.
  echo Install Python 3.11 or newer, enable "Add Python to PATH", then run this file again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating Python virtual environment...
  %PY_CMD% -m venv .venv || goto :fail
) else (
  echo [1/4] Virtual environment already exists.
)

call ".venv\Scripts\activate.bat" || goto :fail

echo [2/4] Checking/installing requirements...
python -m pip install --disable-pip-version-check -r requirements.txt || goto :fail

if not exist ".env" (
  echo [3/4] Creating local .env from .env.example...
  copy /Y ".env.example" ".env" >nul || goto :fail
) else (
  echo [3/4] Existing .env preserved.
)

if not exist "data\uploads" mkdir "data\uploads"
if not exist "backups" mkdir "backups"

echo [4/4] Starting Tender Intelligence...
echo.
echo Local URL: http://127.0.0.1:8000
echo Health:    http://127.0.0.1:8000/api/v1/health
echo Discovery: http://127.0.0.1:8000/discovery
echo Sources:   http://127.0.0.1:8000/sources
echo.
echo Keep the server window open while using the application.

start "Tender Intelligence Server" cmd /k "cd /d ^"%CD%^" ^& call .venv\Scripts\activate.bat ^& uvicorn app.main:app --host 0.0.0.0 --port 8000"

powershell -NoProfile -Command "$ok=$false; 1..30 | ForEach-Object { try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8000/api/v1/health; if($r.StatusCode -eq 200){$ok=$true; break} } catch {}; Start-Sleep -Seconds 1 }; if($ok){exit 0}else{exit 1}"
if errorlevel 1 (
  echo.
  echo [WARNING] The server did not become healthy within 30 seconds.
  echo Check the "Tender Intelligence Server" window for the error message.
  pause
  exit /b 1
)

start "" "http://127.0.0.1:8000"
echo.
echo [OK] Tender Intelligence is running locally.
exit /b 0

:fail
echo.
echo [ERROR] Setup/start failed. Read the message above and send it to ChatGPT.
pause
exit /b 1
