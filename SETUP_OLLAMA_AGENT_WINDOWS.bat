@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Tender Intelligence - Ollama Agent Brain

echo ================================================
echo   Tender Intelligence - Ollama Agent Brain

echo ================================================
echo.
where ollama >nul 2>&1 || (
  echo [ERROR] Ollama was not found on this Windows PC.
  echo Install Ollama for Windows from the official Ollama site, then run this file again.
  echo https://ollama.com/download/windows
  pause
  exit /b 1
)

echo [1/4] Ollama detected.
ollama list >nul 2>&1 || (
  echo [ERROR] Ollama is installed but its local service is not responding.
  echo Start Ollama from the Windows Start menu, wait a few seconds, then retry.
  pause
  exit /b 1
)

echo [2/4] Ensuring qwen3:4b is installed...
ollama list | findstr /I /C:"qwen3:4b" >nul 2>&1
if errorlevel 1 (
  echo Model is not installed. Downloading qwen3:4b now...
  echo This is a local model download and may take time depending on your connection.
  ollama pull qwen3:4b || goto :fail
) else (
  echo [OK] qwen3:4b already installed.
)

echo [3/4] Updating local .env without overwriting other settings...
if not exist ".env" copy /Y ".env.example" ".env" >nul
powershell -NoProfile -Command "$p='.env'; $c=Get-Content $p -Raw; $pairs=@{'OLLAMA_URL'='http://127.0.0.1:11434';'OLLAMA_MODEL'='qwen3:4b';'AUTONOMOUS_AGENTS_ENABLED'='true'}; foreach($k in $pairs.Keys){$v=$pairs[$k]; if($c -match ('(?m)^'+[regex]::Escape($k)+'=.*$')){$c=[regex]::Replace($c,('(?m)^'+[regex]::Escape($k)+'=.*$'),($k+'='+$v))}else{$c=$c.TrimEnd()+[Environment]::NewLine+$k+'='+$v+[Environment]::NewLine}}; Set-Content -Path $p -Value $c -Encoding ascii"

echo [4/4] Verifying Ollama API and model...
powershell -NoProfile -Command "try{$t=Invoke-RestMethod -TimeoutSec 10 'http://127.0.0.1:11434/api/tags'; $names=@($t.models|ForEach-Object {$_.name}); Write-Host ('Installed models: '+($names -join ', ')); if($names -match '^qwen3:4b'){exit 0}else{exit 1}}catch{Write-Host $_.Exception.Message; exit 1}" || goto :fail

echo.
echo [OK] Local Agent Brain is ready: qwen3:4b
echo Restart Tender Intelligence, then open http://127.0.0.1:8000/agents
pause
exit /b 0

:fail
echo.
echo [ERROR] Ollama Agent setup did not complete.
pause
exit /b 1
