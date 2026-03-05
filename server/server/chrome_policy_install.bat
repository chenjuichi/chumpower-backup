@echo off
echo Installing Chrome policy...

powershell -ExecutionPolicy Bypass -File deploy_chrome_policy.ps1

echo.
echo Done.
pause