@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\package.ps1" -Portable
if errorlevel 1 echo Packaging did not finish. See the message above.
pause
