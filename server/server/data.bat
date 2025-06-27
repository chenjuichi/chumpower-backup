@echo off
chcp 65001 >nul
echo 初始化專案及檔案開始
pause

cd database
python dropManyTables.py
python tables.py
python insertPerm.py
python insertUsers.py
python insertAGV.py
python insertCause.py
cd ..

echo 初始化完成
pause
@echo on
