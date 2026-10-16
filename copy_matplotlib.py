import os
import subprocess

cache_root = r"C:\Users\Administrator\AppData\Local\uv\cache\archive-v0"
target_dir = r"E:\miscol\AISing\.venv\Lib\site-packages"

packages = [
    "XcF7bIOKuF813Lvi",  # matplotlib
    "QX6SkJBejTX24n9Q",  # contourpy
    "Va0SBG-SgRqy_BLK",  # kiwisolver
    "Yh_x0iWZO1esgcya",  # pyparsing
    "TEA2U2_LmhBDdgHn",  # python-dateutil
    "uClejRqbV9qjL9q8",  # cycler
    "SkstK1_vrNJu5Rmr",  # charset_normalizer
]

for pkg in packages:
    src = os.path.join(cache_root, pkg)
    if os.path.exists(src):
        print(f"Copying {pkg} -> site-packages...")
        cmd = f'robocopy "{src}" "{target_dir}" /E /MT:16 /NFL /NDL /NJH /NJS /nc /ns /np /R:0 /W:0'
        subprocess.call(cmd, shell=True)

print("Checking rvc_cli...")
cmd = [r"E:\miscol\AISing\.venv\Scripts\python.exe", r"E:\miscol\AISing\rvc-cli\rvc_cli.py", "--help"]
subprocess.call(cmd)
