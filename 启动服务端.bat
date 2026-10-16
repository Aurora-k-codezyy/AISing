@echo off
chcp 65001 >nul
cd /d "%~dp0ai-sing-server"
"%~dp0.venv\Scripts\python.exe" start.py
pause
