import os
import sys
import win32com.client

desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
shell = win32com.client.Dispatch('WScript.Shell')

# 1. Update/Create Desktop Shortcut for Standalone Upgraded Client: 妙唱_云端专业版.lnk
standalone_exe = r'E:\妙唱 云端版\妙唱云端版.exe'
standalone_dir = r'E:\妙唱 云端版'
standalone_lnk = os.path.join(desktop, '妙唱_云端专业版.lnk')

if os.path.exists(standalone_exe):
    sc = shell.CreateShortcut(standalone_lnk)
    sc.TargetPath = standalone_exe
    sc.WorkingDirectory = standalone_dir
    sc.Description = '妙唱 专业版客户端 (已升级直连本地GPU)'
    sc.IconLocation = f'{standalone_exe},0'
    sc.Save()
    print('Updated shortcut:', standalone_lnk, '->', standalone_exe)
else:
    print('Warning: standalone_exe not found:', standalone_exe)

# 2. Update/Create Desktop Shortcut for Python Client: 青玄客户端.lnk
pythonw_exe = r'E:\miscol\AISing\.venv\Scripts\pythonw.exe'
python_client_dir = r'E:\miscol\AISing\ai-sing-client'
client_icon = r'E:\miscol\AISing\ai-sing-client\aising_client\resources\qingxuan.ico'
python_client_lnk = os.path.join(desktop, '青玄客户端.lnk')

if os.path.exists(pythonw_exe):
    sc2 = shell.CreateShortcut(python_client_lnk)
    sc2.TargetPath = r'E:\miscol\AISing\启动青玄客户端.bat'
    sc2.WorkingDirectory = python_client_dir
    sc2.Description = '青玄客户端'
    if os.path.exists(client_icon):
        sc2.IconLocation = f'{client_icon},0'
    sc2.Save()
    print('Updated shortcut:', python_client_lnk)

# 3. Create a bulletproof batch file in E:\妙唱 云端版\启动妙唱_本地直连版.bat
# Using ANSI/GBK encoding so Chinese Windows CMD executes without any encoding error!
standalone_bat = os.path.join(standalone_dir, '启动妙唱_本地直连版.bat')
bat_content_gbk = (
    '@echo off\r\n'
    'cd /d "%~dp0"\r\n'
    'set "AIS_CLIENT_API_BASE_URL=http://127.0.0.1:8200"\r\n'
    'set "AIS_CLIENT_EDITION=full"\r\n'
    'for %%i in ("%~dp0*.exe") do (\r\n'
    '    start "" "%%~fi"\r\n'
    '    goto :done\r\n'
    ')\r\n'
    ':done\r\n'
    'exit\r\n'
).encode('gbk')

with open(standalone_bat, 'wb') as f:
    f.write(bat_content_gbk)
print('Updated batch file:', standalone_bat)

# 4. Create bulletproof batch file in E:\miscol\AISing\启动妙唱客户端.bat
local_bat = r'E:\miscol\AISing\启动妙唱客户端.bat'
local_bat_content = (
    '@echo off\r\n'
    'cd /d "%~dp0ai-sing-client"\r\n'
    'set "AIS_CLIENT_API_BASE_URL=http://127.0.0.1:8200"\r\n'
    'set "AIS_CLIENT_EDITION=full"\r\n'
    'start "" "%~dp0.venv\\Scripts\\pythonw.exe" -m aising_client.main\r\n'
    'exit\r\n'
).encode('gbk')

with open(local_bat, 'wb') as f:
    f.write(local_bat_content)
print('Updated batch file:', local_bat)

print('All shortcuts and batch files successfully configured!')
