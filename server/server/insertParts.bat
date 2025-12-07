chcp 65001 >nul
echo 準備讀取exce檔案,並匯入p_part table
pause

python -m database.p_part_loader

echo 匯入完成...
pause

@echo on