@echo off
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup.ps1"
set "VIDEO_TOOLS_EXIT=%errorlevel%"
if not "%VIDEO_TOOLS_EXIT%"=="0" echo The operation did not finish. See the message above.
pause
exit /b %VIDEO_TOOLS_EXIT%
