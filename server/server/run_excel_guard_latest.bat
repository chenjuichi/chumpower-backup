@echo off
cd /d %~dp0
REM 掃描 D:\chumpower_data 取最新 .xlsx 執行
python "%~dp0excel_guard.py" --latest
pause
