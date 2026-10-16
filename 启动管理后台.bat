@echo off
chcp 65001 >nul
cd /d "%~dp0ai-sing-admin"
npm run dev
pause
