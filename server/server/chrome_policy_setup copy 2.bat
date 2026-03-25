@echo off
chcp 65001 > nul
setlocal

:: ---------- 自動提升為系統管理員 ----------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privilege...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================
echo  Chrome Policy Auto Setup
echo  (Create directories + create .reg + import)
echo ============================================
echo.

REM Create policy folder (usually not required, but for safety)
echo Creating policy directory...
mkdir "C:\Windows\System32\GroupPolicy\Machine" 2>nul
mkdir "C:\Windows\System32\GroupPolicy\User" 2>nul

REM Generate the reg file
echo Creating chrome_policies.reg...
(
echo Windows Registry Editor Version 5.00
echo.
echo [HKEY_LOCAL_MACHINE\Software\Policies\Google\Chrome]
echo "WebRtcAllowLegacyGlobalIpAddress"=dword:00000001
echo "TreatInsecureOriginAsSecure"="http://192.168.68.56:8060,http://192.168.68.56"
) > "%temp%\chrome_policies.reg"

if not exist "%temp%\chrome_policies.reg" (
    echo Failed to create reg file.
    pause
    exit /b 1
)

echo Done.
echo.

REM Import the registry entries
echo Importing chrome_policies.reg ...
reg import "%temp%\chrome_policies.reg"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to import registry.
    echo Please confirm this BAT is running as Administrator.
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