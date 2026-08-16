@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Tender Intelligence - Live Coverage Benchmark

if not exist data mkdir data

echo ================================================
echo   Live Coverage Benchmark

echo ================================================
echo.
echo This runs the SAME bounded query set across every available provider.
echo It can take several minutes depending on Google/Bing/DDG response times.
echo.

powershell -NoProfile -Command "$uri='http://127.0.0.1:8000/api/v1/discovery/coverage/benchmark?query_limit=5&result_limit=10'; try { $r=Invoke-RestMethod -Method Post -TimeoutSec 600 $uri; $json=$r|ConvertTo-Json -Depth 12; $json|Set-Content -Encoding UTF8 'data\coverage_benchmark_latest.json'; Write-Host ''; Write-Host '=== LIVE COMPARISON ==='; $r.comparison|Select-Object provider,runs,ok_runs,results,distinct_urls,distinct_domains,unique_urls_vs_others,new_domains,new_candidates,share_of_union_pct|Format-Table -AutoSize; Write-Host ('Union distinct URLs: '+$r.union_distinct_urls); Write-Host ''; Write-Host '[OK] Saved: data\coverage_benchmark_latest.json'; exit 0 } catch { Write-Host '[ERROR] Benchmark failed.'; Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 (
  echo.
  echo Make sure Tender Intelligence is running on port 8000 and SearXNG is running if you want Google/Bing included.
  pause
  exit /b 1
)

echo.
pause
