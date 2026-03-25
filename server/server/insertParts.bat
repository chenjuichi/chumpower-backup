chcp 65001 >nul
echo 準備讀取exce檔案,並匯入p_part table
pause

cd database

python -m p_part_loader

cd ..

echo 匯入完成...
pause

@echo on