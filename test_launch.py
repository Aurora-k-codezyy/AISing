import subprocess

bat = r"E:\妙唱 云端版\启动妙唱_本地直连版.bat"
print("Launching:", bat)
ret = subprocess.run(["cmd.exe", "/c", f'"{bat}"'], capture_output=True, text=True)
print("Returncode:", ret.returncode)
print("Stdout:", ret.stdout)
print("Stderr:", ret.stderr)
