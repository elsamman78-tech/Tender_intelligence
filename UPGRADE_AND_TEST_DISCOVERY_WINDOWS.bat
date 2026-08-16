@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Tender Intelligence - Upgrade and Test Discovery

echo ======================================================
echo   Tender Intelligence - Upgrade + Search + Agent Test
echo ======================================================
echo.
echo This will preserve local .env, database, .venv and backups.
echo Close the existing Tender Intelligence server before continuing.
echo.
pause

if not exist "UPDATE_CODE_WINDOWS.bat" (
  echo [ERROR] UPDATE_CODE_WINDOWS.bat is missing.
  pause
  exit /b 1
)

echo.
echo [1/6] Updating application code safely...
call "UPDATE_CODE_WINDOWS.bat"
if errorlevel 1 goto :fail

echo.
echo [2/6] Starting local SearXNG...
where docker >nul 2>&1 || goto :docker_missing
docker info >nul 2>&1 || goto :docker_not_running
call "START_SEARXNG_WINDOWS.bat"
if errorlevel 1 goto :fail

echo.
echo [3/6] Preparing Ollama Agent Brain if Ollama is installed...
where ollama >nul 2>&1
if errorlevel 1 (
  echo [WARN] Ollama is not installed. The application will use the bounded deterministic agent fallback.
  echo You can install Ollama later and run SETUP_OLLAMA_AGENT_WINDOWS.bat.
) else (
  call "SETUP_OLLAMA_AGENT_WINDOWS.bat"
  if errorlevel 1 echo [WARN] Ollama setup did not complete. Continuing with deterministic fallback.
)

echo.
echo [4/6] Starting Tender Intelligence...
call "RUN_LOCAL_WINDOWS.bat"
if errorlevel 1 goto :fail

echo.
echo [5/6] Verifying Google, Bing, SearXNG and provider status...
call "VERIFY_SEARCH_STACK_WINDOWS.bat"
if errorlevel 1 goto :fail

echo.
echo [6/6] Running first live Coverage Benchmark...
call "RUN_COVERAGE_BENCHMARK_WINDOWS.bat"
if errorlevel 1 goto :fail

echo.
echo ======================================================
echo [OK] Upgrade and verification workflow completed.
echo ======================================================
echo Dashboard:      http://127.0.0.1:8000/
echo Discovery:      http://127.0.0.1:8000/discovery
echo Country Coverage:http://127.0.0.1:8000/coverage/countries
echo Source Health:  http://127.0.0.1:8000/system/source-health
echo Agents:         http://127.0.0.1:8000/agents
echo Benchmark JSON: data\coverage_benchmark_latest.json
echo.
start "" "http://127.0.0.1:8000/discovery"
pause
exit /b 0

:docker_missing
echo.
echo [STOP] Docker Desktop is not installed.
echo SearXNG, Google and Bing cannot be verified until Docker Desktop is installed.
echo The application code update is already safe and complete.
pause
exit /b 2

:docker_not_running
echo.
echo [STOP] Docker Desktop is installed but the Docker engine is not running.
echo Start Docker Desktop, wait until it says it is ready, then run this file again.
pause
exit /b 3

:fail
echo.
echo [ERROR] The workflow stopped at the step above.
echo Existing local data was not intentionally deleted; UPDATE_CODE_WINDOWS.bat keeps backups.
pause
exit /b 1
