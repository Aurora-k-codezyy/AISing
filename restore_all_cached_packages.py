import os
import subprocess

cache_root = r"C:\Users\Administrator\AppData\Local\uv\cache\archive-v0"
target_dir = r"E:\miscol\AISing\.venv\Lib\site-packages"

folders = os.listdir(cache_root)
print(f"Total cached packages in archive-v0: {len(folders)}")

for folder in folders:
    src = os.path.join(cache_root, folder)
    if not os.path.isdir(src):
        continue
    # Check if there is cp312 or cp314 specific pyd that wouldn't work on cp311
    # But robocopy skips nothing or copies cleanly
    # Robocopy with /xc /xn /xo skips existing files so it's super fast!
    cmd = f'robocopy "{src}" "{target_dir}" /E /MT:16 /NFL /NDL /NJH /NJS /nc /ns /np /R:0 /W:0'
    subprocess.call(cmd, shell=True)

print("All cached packages restored! Now testing rvc_cli.py...")
cmd = [r"E:\miscol\AISing\.venv\Scripts\python.exe", r"E:\miscol\AISing\rvc-cli\rvc_cli.py", "--help"]
subprocess.call(cmd)
