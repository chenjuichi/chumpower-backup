@echo off
setlocal
chcp 65001 >nul

echo mySQL資料庫內table column新增開始
pause

:: 設定 MySQL 登入帳號與密碼
set MYSQL_USER=root
set MYSQL_PWD=77974590
set MYSQL_DB=chumpower

echo ===============================================
echo   開始修改資料表 material (新增欄位)
echo ===============================================

:: 執行 ALTER TABLE 新增欄位
mysql -u %MYSQL_USER% -p%MYSQL_PWD% %MYSQL_DB% -e ^
"ALTER TABLE material
    ADD COLUMN IF NOT EXISTS sd_time_B100 VARCHAR(30),
    ADD COLUMN IF NOT EXISTS sd_time_B102 VARCHAR(30),
    ADD COLUMN IF NOT EXISTS sd_time_B103 VARCHAR(30),
    ADD COLUMN IF NOT EXISTS sd_time_B107 VARCHAR(30),
    ADD COLUMN IF NOT EXISTS sd_time_B108 VARCHAR(30),
    ADD COLUMN IF NOT EXISTS move_by_automatic_or_manual_2 TINYINT(1) NOT NULL DEFAULT 1;"

if %ERRORLEVEL%==0 (
    echo 已成功新增欄位到 material table.
) else (
    echo 新增欄位失敗，請檢查 MySQL 連線資訊或語法.
)

echo 初始化完成
pause
endlocal
@echo on
