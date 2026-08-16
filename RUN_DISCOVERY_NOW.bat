@echo off
powershell -NoProfile -Command "try { Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/discovery/run | ConvertTo-Json -Depth 8 } catch { Write-Host $_.Exception.Message; exit 1 }"
pause
