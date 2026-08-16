@echo off
setlocal
cd /d "%~dp0"
title Tender Intelligence - Local Launcher
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_local_windows.ps1"
exit /b %ERRORLEVEL%
