import os
import subprocess
import sys
from pathlib import Path

urls = [
    "https://mirrors.aliyun.com/pytorch-wheels/cu124/torch-2.6.0%2Bcu124-cp311-cp311-win_amd64.whl",
    "https://mirrors.aliyun.com/pytorch-wheels/cu124/torchaudio-2.6.0%2Bcu124-cp311-cp311-win_amd64.whl",
    "https://mirrors.aliyun.com/pytorch-wheels/cu124/torchvision-0.21.0%2Bcu124-cp311-cp311-win_amd64.whl",
]

download_dir = Path("E:/miscol/AISing/downloads")
download_dir.mkdir(parents=True, exist_ok=True)

for url in urls:
    fname = url.split("/")[-1].replace("%2B", "+")
    dest = download_dir / fname
    aria2_control = download_dir / (fname + ".aria2")
    if dest.exists() and not aria2_control.exists() and dest.stat().st_size > 1024 * 1024:
        print(f"Already fully downloaded: {dest} ({dest.stat().st_size / 1024 / 1024:.2f} MB)")
        continue
    print(f"Downloading/Resuming {fname} via aria2c (no proxy, 16 connections)...")
    cmd = [
        "aria2c",
        "--all-proxy=",
        "-c",  # resume
        "-x", "16",
        "-s", "16",
        "-k", "1M",
        "-U", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "-d", str(download_dir),
        "-o", fname,
        url,
    ]
    ret = subprocess.call(cmd)
    if ret != 0:
        print(f"Download failed for {url}")
        sys.exit(ret)

print("All wheels downloaded successfully! Now installing into .venv...")
wheels = [
    download_dir / "torch-2.6.0+cu124-cp311-cp311-win_amd64.whl",
    download_dir / "torchaudio-2.6.0+cu124-cp311-cp311-win_amd64.whl",
    download_dir / "torchvision-0.21.0+cu124-cp311-cp311-win_amd64.whl",
]
install_cmd = [
    "uv", "pip", "install",
    *[str(w) for w in wheels],
    "--default-index", "https://mirrors.aliyun.com/pypi/simple/",
    "--python", r"E:\miscol\AISing\.venv\Scripts\python.exe",
]
print("Running:", " ".join(install_cmd))
ret = subprocess.call(install_cmd)
if ret != 0:
    print("Wheel installation failed!")
    sys.exit(ret)

# Also install torchcrepe
print("Installing torchcrepe and other dependencies...")
dep_cmd = [
    "uv", "pip", "install",
    "torchcrepe", "scipy", "librosa", "soundfile",
    "--default-index", "https://mirrors.aliyun.com/pypi/simple/",
    "--python", r"E:\miscol\AISing\.venv\Scripts\python.exe",
]
subprocess.call(dep_cmd)

print("Verifying torch CUDA...")
test_cmd = [
    r"E:\miscol\AISing\.venv\Scripts\python.exe",
    "-c",
    "import torch, torchaudio, torchcrepe; print('Torch:', torch.__version__, 'CUDA:', torch.cuda.is_available(), 'Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
]
subprocess.call(test_cmd)
