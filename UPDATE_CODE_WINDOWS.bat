@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Tender Intelligence - Safe Updater

echo ================================================
echo   Tender Intelligence - Safe Code Update
echo ================================================
echo.
if not exist backups mkdir backups
for /f "tokens=1-3 delims=/: " %%a in ("%date%") do set DS=%%c%%b%%a
set TS=%time::=%
set TS=%TS: =0%
set TS=%TS:.=%

if exist "data\tenders.db" copy /Y "data\tenders.db" "backups\tenders_before_update_%DS%_%TS%.db" >nul
if exist ".env" copy /Y ".env" "backups\env_before_update_%DS%_%TS%.txt" >nul

echo [1/4] Downloading latest main branch...
set "TMPROOT=%TEMP%\tender_intelligence_update_%RANDOM%"
mkdir "%TMPROOT%" >nul 2>&1
powershell -NoProfile -Command "Invoke-WebRequest 'https://github.com/elsamman78-tech/Tender_intelligence/archive/refs/heads/main.zip' -OutFile '%TMPROOT%\main.zip'" || goto :fail

echo [2/4] Extracting...
powershell -NoProfile -Command "Expand-Archive -Path '%TMPROOT%\main.zip' -DestinationPath '%TMPROOT%' -Force" || goto :fail

echo [3/4] Updating code while preserving .env, data, .venv and backups...
robocopy "%TMPROOT%\Tender_intelligence-main" "%CD%" /E /R:2 /W:1 /XD data .venv backups .git __pycache__ /XF .env >nul
if errorlevel 8 goto :fail

echo [4/4] Cleaning temporary files...
rmdir /S /Q "%TMPROOT%" >nul 2>&1

echo.
echo [OK] Code updated. Local database and .env were preserved.
echo A backup was created in the backups folder when local data existed.
echo.
echo Run RUN_LOCAL_WINDOWS.bat to start the updated application.
pause
exit /b 0

:fail
echo.
echo [ERROR] Update failed. Your existing data was not deleted.
echo Check the message above or send a screenshot to ChatGPT.
pause
exit /b 1
