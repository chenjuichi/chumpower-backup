@echo off
chcp 65001 >nul
echo 複製檔案開始
pause

:: client端, 確保目標目錄存在
if not exist "C:\chumpower-backup\front"                        mkdir "C:\chumpower-backup\front"
if not exist "C:\chumpower-backup\front\public"                 mkdir "C:\chumpower-backup\front\public"
if not exist "C:\chumpower-backup\front\src"                    mkdir "C:\chumpower-backup\front\src"
if not exist "C:\chumpower-backup\front\src\views"              mkdir "C:\chumpower-backup\front\src\views"
if not exist "C:\chumpower-backup\front\src\views\old_source"   mkdir "C:\chumpower-backup\front\src\views\old_source"
if not exist "C:\chumpower-backup\front\src\styles"             mkdir "C:\chumpower-backup\front\src\styles"
if not exist "C:\chumpower-backup\front\src\store"              mkdir "C:\chumpower-backup\front\src\store"
if not exist "C:\chumpower-backup\front\src\router"             mkdir "C:\chumpower-backup\front\src\router"
if not exist "C:\chumpower-backup\front\src\router\old_source"  mkdir "C:\chumpower-backup\front\src\router\old_source"
if not exist "C:\chumpower-backup\front\src\mixins"             mkdir "C:\chumpower-backup\front\src\mixins"
if not exist "C:\chumpower-backup\front\src\components"         mkdir "C:\chumpower-backup\front\src\components"
if not exist "C:\chumpower-backup\front\src\assets"             mkdir "C:\chumpower-backup\front\src\assets"

:: client端, 開始複製檔案
copy "D:\vue3\chumpower\*.js"       "C:\chumpower-backup\front\"
copy "D:\vue3\chumpower\*.json"     "C:\chumpower-backup\front\"
copy "D:\vue3\chumpower\*.bat"      "C:\chumpower-backup\front\"
copy "D:\vue3\chumpower\.env"       "C:\chumpower-backup\front\"
copy "D:\vue3\chumpower\.gitignore" "C:\chumpower-backup\front\"

copy "D:\vue3\chumpower\public\*.json" "C:\chumpower-backup\front\public\"

copy "D:\vue3\chumpower\src\views\*.vue"            "C:\chumpower-backup\front\src\views"
copy "D:\vue3\chumpower\src\styles\*.*"             "C:\chumpower-backup\front\src\styles"
copy "D:\vue3\chumpower\src\store\*.*"              "C:\chumpower-backup\front\src\store"
copy "D:\vue3\chumpower\src\router\*.*"             "C:\chumpower-backup\front\src\router"
copy "D:\vue3\chumpower\src\mixins\*.*"             "C:\chumpower-backup\front\src\mixins"
copy "D:\vue3\chumpower\src\components\*.*"         "C:\chumpower-backup\front\src\components"
copy "D:\vue3\chumpower\src\assets\*.*"             "C:\chumpower-backup\front\src\assets"

copy "D:\vue3\chumpower\src\views\old_source\*.vue" "C:\chumpower-backup\front\src\views\old_source"
copy "D:\vue3\chumpower\src\router\old_source\*.js" "C:\chumpower-backup\front\src\router\old_source"

:: server端, 檢查並建立其他必要目錄
if not exist "C:\chumpower-backup\server\server" (
    echo 建立目錄: C:\chumpower-backup\server\server
    mkdir "C:\chumpower-backup\server\server"
)
copy "C:\vue\chumpower\途程說明-0609-m.xlsx" "C:\chumpower-backup\server"
copy "C:\vue\chumpower\server\*.py" "C:\chumpower-backup\server\server"
copy "C:\vue\chumpower\server\*.bat" "C:\chumpower-backup\server\server"

if not exist "C:\chumpower-backup\server\server\database" (
    echo 建立目錄: C:\chumpower-backup\server\server\database
    mkdir "C:\chumpower-backup\server\server\database"
)
copy "C:\vue\chumpower\server\database\*.py" "C:\chumpower-backup\server\server\database"

if not exist "C:\chumpower-backup\server\server\ajax" (
    echo 建立目錄: C:\chumpower-backup\server\server\ajax
    mkdir "C:\chumpower-backup\server\server\ajax"
)
copy "C:\vue\chumpower\server\ajax\*.py" "C:\chumpower-backup\server\server\ajax"

if not exist "C:\chumpower-backup\server\pdf_file\領退料單" (
    echo 建立目錄: C:\chumpower-backup\server\pdf_file\領退料單
    mkdir "C:\chumpower-backup\server\pdf_file\領退料單"
)
copy "C:\vue\chumpower\pdf_file\領退料單\*.*" "C:\chumpower-backup\server\pdf_file\領退料單"

if not exist "C:\chumpower-backup\server\pdf_file\物料清單" (
    echo 建立目錄: C:\chumpower-backup\server\pdf_file\物料清單
    mkdir "C:\chumpower-backup\server\pdf_file\物料清單"
)
copy "C:\vue\chumpower\pdf_file\物料清單\*.*" "C:\chumpower-backup\server\pdf_file\物料清單"

if not exist "C:\chumpower-backup\server\日期章" (
    echo 建立目錄: C:\chumpower-backup\server\日期章
    mkdir "C:\chumpower-backup\server\日期章"
)
copy "C:\vue\chumpower\日期章\*.png" "C:\chumpower-backup\server\日期章"

::if not exist "C:\chumpower-backup\server\server\travel" (
::    echo 建立目錄: C:\chumpower-backup\server\server\travel
::    mkdir "C:\chumpower-backup\server\server\travel"
::)
::copy "C:\vue\chumpower\server\travel\*.py" "C:\chumpower-backup\server\server\travel"

:: 確保目標目錄存在
if not exist "C:\chumpower-backup\gateway"                        mkdir "C:\chumpower-backup\gateway"
copy "D:\vue\meet\app.js" "C:\chumpower-backup\gateway"
copy "D:\vue\meet\*.json" "C:\chumpower-backup\gateway"
copy "D:\vue\meet\.env" "C:\chumpower-backup\gateway"
copy "D:\vue\meet\update-env.js" "C:\chumpower-backup\gateway"
copy "D:\vue\meet\service.log" "C:\chumpower-backup\gateway"
copy "D:\vue\meet\ip-log.txt" "C:\chumpower-backup\gateway"

:: 確保目標目錄存在
if not exist "C:\chumpower-backup\console"                        mkdir "C:\chumpower-backup\console"
xcopy "C:\vue\chumpower\console\SocketIOServer" "C:\chumpower-backup\console\SocketIOServer" /E /I /Y

if not exist "C:\chumpower-backup\console2"                        mkdir "C:\chumpower-backup\console2"
xcopy "C:\vue\chumpower\console2\TestSocketIOServer" "C:\chumpower-backup\console2\TestSocketIOServer" /E /I /Y

echo 複製完成
pause

REM 取得 yyyy-mm-dd 格式日期
for /f "tokens=1-3 delims=- " %%a in ('powershell -command "Get-Date -Format yyyy-MM-dd"') do (
    set TODAY=%%a
)

echo 準備進行git
pause

REM Git 操作
git add .
git commit -m "%TODAY%"
git push --all origin

echo git完成
pause

@echo on
