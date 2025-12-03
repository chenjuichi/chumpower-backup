chcp 65001 >nul
echo 初始化專案及檔案開始
pause

REM 1) 產生 SQL
python database\print_p_tables_sql.py > database\p_tables_ddl.sql
IF ERRORLEVEL 1 (
    echo 產生 p_tables_ddl.sql 失敗, 中止匯入流程
    goto END
)

REM 2) 關掉 FK 檢查
REM mysql -uroot -p77974590 -e "SET FOREIGN_KEY_CHECKS = 0;" chumpower

REM 3) 匯入 DDL
mysql -uroot -p77974590 chumpower < database\p_tables_ddl.sql

REM 4) 打開 FK 檢查
REM mysql -uroot -p77974590 -e "SET FOREIGN_KEY_CHECKS = 1;" chumpower

echo.
echo 完成匯入 p_tables_ddl.sql

:END
pause
@echo on