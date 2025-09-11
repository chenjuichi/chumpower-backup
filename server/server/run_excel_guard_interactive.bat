@echo off
cd /d %~dp0
REM 互動選檔執行（預設資料夾 D:\chumpower_data）
python "%~dp0excel_guard.py" --interactive
pause
