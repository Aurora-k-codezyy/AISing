@echo off
chcp 65001 >nul
cd /d "%~dp0ai-sing-client"
set "AIS_CLIENT_API_BASE_URL=http://127.0.0.1:8200"
set "AIS_CLIENT_EDITION=cloud"
start "" "%~dp0.venv\Scripts\pythonw.exe" -m aising_client.main
exit
