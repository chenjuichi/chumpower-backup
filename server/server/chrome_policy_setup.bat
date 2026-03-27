@echo off
chcp 65001 > nul
setlocal

echo 設定 Chrome 下載政策...

:: 建立政策路徑
reg add "HKLM\Software\Policies\Google\Chrome" /f

:: 1. 關閉危險下載警告（核心）
reg add "HKLM\Software\Policies\Google\Chrome" /v DownloadRestrictions /t REG_DWORD /d 0 /f

:: 2. 允許特定副檔名
reg add "HKLM\Software\Policies\Google\Chrome" /v ExemptFileTypeDownloadWarnings /t REG_SZ /d "exe,bat,msi,zip" /f

:: 3. 允許內網當安全來源（很重要）
reg add "HKLM\Software\Policies\Google\Chrome" /v TreatInsecureOriginAsSecure /t REG_SZ /d "http://192.168.68.56" /f

:: 4. 關閉不安全下載警告
reg add "HKLM\Software\Policies\Google\Chrome" /v InsecureDownloadWarningsEnabled /t REG_DWORD /d 0 /f

echo 完成，請重新開啟 Chrome
pause