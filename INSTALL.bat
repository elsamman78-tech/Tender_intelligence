@echo off
setlocal
cd /d %~dp0
where py >nul 2>&1 || (echo Python 3.11+ is required. & pause & exit /b 1)
if not exist .venv py -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
copy /Y .env.example .env >nul 2>&1
echo.
echo Installation finished. No paid API key was requested.
echo Run START.bat
pause
