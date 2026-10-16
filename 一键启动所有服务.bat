@echo off
chcp 65001 >nul
echo ========================================================
echo               AI-Sing 音乐系统 一键启动
echo ========================================================

echo [1/3] 正在启动后端服务 (8200)...
start "AI-Sing 后端服务 [8200]" cmd /c "cd /d %~dp0ai-sing-server && %~dp0.venv\Scripts\python.exe start.py"

echo [2/3] 正在启动管理后台 (5173)...
start "AI-Sing 管理后台 [5173]" cmd /c "cd /d %~dp0ai-sing-admin && npm.cmd run dev"

echo [3/3] 正在启动客户端...
cd /d "%~dp0ai-sing-client"
set "AIS_CLIENT_API_BASE_URL=http://127.0.0.1:8200"
set "AIS_CLIENT_EDITION=cloud"
start "" "%~dp0.venv\Scripts\pythonw.exe" -m aising_client.main

echo ========================================================
echo 所有服务已启动完成！
echo - 后端服务: http://127.0.0.1:8200 (API ^& 文档 /docs)
echo - 管理后台: http://127.0.0.1:5173
echo - 桌面客户端已在后台启动
echo ========================================================
ping 127.0.0.1 -n 4 >nul
exit
