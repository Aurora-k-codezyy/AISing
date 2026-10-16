import os
import subprocess

cache_root = r"C:\Users\Administrator\AppData\Local\uv\cache\archive-v0"
target_dir = r"E:\miscol\AISing\.venv\Lib\site-packages"

packages = [
    "knKIwwC3VA-q00Lg",  # librosa
    "hB_8htHpKVO6ZBH5",  # scipy
    "S_G58ToABVh95h0E",  # numba
    "jGEGrpo9chDsTjQ4",  # resampy
    "rxpcBf8BUNuqEesl",  # llvmlite
    "X-pd7JfsP5WqYgC_",  # pooch
    "yCngqUhdP1jCy7Qi",  # lazy_loader
]

for pkg in packages:
    src = os.path.join(cache_root, pkg)
    if os.path.exists(src):
        print(f"Copying {pkg} -> site-packages...")
        cmd = f'robocopy "{src}" "{target_dir}" /E /MT:16 /NFL /NDL /NJH /NJS /nc /ns /np /R:0 /W:0'
        subprocess.call(cmd, shell=True)

print("Verifying audio stack in .venv...")
test_script = """
import torch
import torchaudio
import torchcrepe
import librosa
import scipy
print('Torch:', torch.__version__)
print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))
print('Torchaudio:', torchaudio.__version__)
print('Torchcrepe: OK')
print('Librosa:', librosa.__version__)
"""
subprocess.call([r"E:\miscol\AISing\.venv\Scripts\python.exe", "-c", test_script])
