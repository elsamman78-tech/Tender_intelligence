@echo off
cd /d %~dp0
if not exist backups mkdir backups
powershell -NoProfile -Command "$ts=Get-Date -Format yyyyMMdd_HHmmss; Compress-Archive -Path data -DestinationPath ('backups\tender_backup_'+$ts+'.zip') -Force"
echo Backup created in backups folder.
pause
