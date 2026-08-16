@echo off
cd /d %~dp0
if not exist .venv\Scripts\python.exe (echo Run INSTALL.bat first.& pause& exit /b 1)
call .venv\Scripts\activate.bat
start "Tender Intelligence" cmd /k "uvicorn app.main:app --host 0.0.0.0 --port 8000"
timeout /t 2 >nul
start http://127.0.0.1:8000
