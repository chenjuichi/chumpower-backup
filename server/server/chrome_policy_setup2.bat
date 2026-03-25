@echo off
chcp 65001 > nul
setlocal

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privilege...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================
echo  Chrome Policy Auto Setup
echo ============================================
echo.

reg add "HKEY_LOCAL_MACHINE\Software\Policies\Google\Chrome" /v "WebRtcAllowLegacyGlobalIpAddress" /t REG_DWORD /d 1 /f
if %errorlevel% neq 0 (
    echo Failed to set WebRtcAllowLegacyGlobalIpAddress
    pause
    exit /b 1
)

reg add "HKEY_LOCAL_MACHINE\Software\Policies\Google\Chrome" /v "TreatInsecureOriginAsSecure" /t REG_SZ /d "http://192.168.68.56:8060,http://192.168.68.56" /f
if %errorlevel% neq 0 (
    echo Failed to set TreatInsecureOriginAsSecure
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Completed!
echo  Restart Chrome and check: chrome://policy
echo ============================================
pause
exit /b 0