@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Stopping all Smiger Bot services ...
docker compose down
echo Done.
pause
