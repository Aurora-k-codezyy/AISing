import subprocess
import sys

url = "https://mirrors.aliyun.com/pytorch-wheels/cu124/torch-2.6.0%2Bcu124-cp311-cp311-win_amd64.whl"
cmd = [
    "aria2c",
    "-x", "16",
    "-s", "16",
    "-k", "1M",
    "-U", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "-d", "E:/miscol/AISing/downloads",
    url,
]
print("Running:", cmd)
sys.exit(subprocess.call(cmd))
