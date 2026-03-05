@echo off
chcp 65001 > nul
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
) > chrome_policies.reg

echo Done.
echo.

REM Import the registry entries
echo Importing chrome_policies.reg ...
reg import chrome_policies.reg

echo.
echo ============================================
echo  Completed!
echo  Restart Chrome and check: chrome://policy
echo ============================================
pause