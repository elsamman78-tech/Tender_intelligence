@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Tender Intelligence - Verify Search Stack

echo ================================================
echo   Verify Search Stack - SearXNG / Google / Bing
echo ================================================
echo.

echo [1/4] SearXNG Meta API...
powershell -NoProfile -Command "try{$r=Invoke-RestMethod -TimeoutSec 20 'http://127.0.0.1:8888/search?q=engineering+consultancy+tender&format=json'; if($null -ne $r.results){Write-Host ('[OK] META results: '+$r.results.Count); exit 0}else{exit 1}}catch{Write-Host $_.Exception.Message; exit 1}" || goto :searx_fail

echo [2/4] Google engine through local SearXNG...
powershell -NoProfile -Command "try{$r=Invoke-RestMethod -TimeoutSec 25 'http://127.0.0.1:8888/search?q=engineering+consultancy+tender&format=json&engines=google'; Write-Host ('[OK] GOOGLE results: '+$r.results.Count); if($r.unresponsive_engines){Write-Host ('Unresponsive: '+($r.unresponsive_engines|ConvertTo-Json -Compress))}; exit 0}catch{Write-Host $_.Exception.Message; exit 1}" || echo [WARN] Google engine did not answer successfully.

echo [3/4] Bing engine through local SearXNG...
powershell -NoProfile -Command "try{$r=Invoke-RestMethod -TimeoutSec 25 'http://127.0.0.1:8888/search?q=engineering+consultancy+tender&format=json&engines=bing'; Write-Host ('[OK] BING results: '+$r.results.Count); if($r.unresponsive_engines){Write-Host ('Unresponsive: '+($r.unresponsive_engines|ConvertTo-Json -Compress))}; exit 0}catch{Write-Host $_.Exception.Message; exit 1}" || echo [WARN] Bing engine did not answer successfully.

echo [4/4] Tender Intelligence provider status...
powershell -NoProfile -Command "try{$r=Invoke-RestMethod -TimeoutSec 15 'http://127.0.0.1:8000/api/v1/discovery/status'; $r.providers|Format-Table -AutoSize; exit 0}catch{Write-Host '[WARN] Tender Intelligence is not running or status endpoint failed.'; Write-Host $_.Exception.Message; exit 1}"

echo.
echo Verification finished. Open http://127.0.0.1:8000/discovery to see provider status.
pause
exit /b 0

:searx_fail
echo.
echo [ERROR] Local SearXNG is not responding on http://127.0.0.1:8888
echo Run START_SEARXNG_WINDOWS.bat first.
pause
exit /b 1
