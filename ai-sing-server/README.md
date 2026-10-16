# AI Sing Server

FastAPI backend for uploads, a MySQL task queue, RVC training and inference, and Demucs vocal separation.


## Docker部署命令
docker build -t ai-sing-server:local .

docker compose down

docker compose up -d --force-recreate

docker compose logs -f ai-sing-server

## 1Panel GPU Deployment

Do not deploy this service with `Websites -> Runtime Environment -> Python`. This service includes GPU PyTorch, RVC, and Demucs, so its dependencies should be installed when a Docker image is built, not each time a runtime container starts.

Use `Containers -> Images -> Build Image` first to build the included `Dockerfile` as the local image `ai-sing-server:local`. Then use `Containers -> Compose` to start `docker-compose.yml`, which is configured to use that local image without pulling it from Docker Hub.

### Directory Layout

The current `server` directory is the deployment root. On Ubuntu, upload its contents directly to:

```text
/home/1panelProject/python/ai-sing-server/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── start.py
├── .env
├── app/
├── scripts/
├── data/                 # Runtime data, persisted by volume mount
└── logs/                 # Runtime logs, persisted by volume mount
```

Do not create another child `server/` directory or copy RVC CLI into this project. This deployment reuses the existing host directory `/opt/rvc-cli`.

### Use Existing RVC CLI

Your server already has RVC CLI at `/opt/rvc-cli`. Keep that directory outside the application project so it survives image rebuilds. Verify that its entrypoint exists:

```bash
test -f /opt/rvc-cli/rvc_cli.py && echo "RVC CLI source exists"
```

For the configured `40k + RMVPE + contentvec` workflow, these existing resource files are required under `/opt/rvc-cli`:

```text
/opt/rvc-cli/assets/config.json
/opt/rvc-cli/rvc/models/pretraineds/hifi-gan/f0G40k.pth
/opt/rvc-cli/rvc/models/pretraineds/hifi-gan/f0D40k.pth
/opt/rvc-cli/rvc/models/predictors/rmvpe.pt
/opt/rvc-cli/rvc/models/embedders/contentvec/pytorch_model.bin
/opt/rvc-cli/rvc/models/embedders/contentvec/config.json
```

The compose file mounts the host path `/opt/rvc-cli` at the identical path inside the application container. The provided `.env` command templates already use `/opt/rvc-cli`.
The training adapter creates a minimal `/opt/rvc-cli/assets/config.json` automatically when that export metadata file is missing, without replacing an existing Applio configuration.

### Configure

Configuration lives in `.env`. It already includes database settings and command templates for training and song processing.

Keep the RVC command settings in the container form:

```env
AIS_RVC_TRAIN_COMMAND=python scripts/rvc/train_cli.py --input "{input}" --output-dir "{model_dir}" --job-id "{job_id}" --rvc-root /opt/rvc-cli --rvc-python python --gpu 0 --sample-rate 40000 --epochs 200 --batch-size 8 --save-every-epoch 10 --cpu-cores 4 --include-mutes 2 --cut-preprocess Automatic
AIS_DEMUCS_COMMAND=python -m demucs --two-stems=vocals --out "{demucs_dir}" "{input}"
AIS_RVC_INFER_COMMAND=python scripts/rvc/infer_cli.py --input "{vocals}" --model "{model_path}" --output "{ai_vocal}" --rvc-root /opt/rvc-cli --rvc-python python --pitch 0 --index-rate 0.3 --f0-method rmvpe
```

Do not change these paths to a host virtual environment. `python` here means the interpreter inside the built container image.

### Configure Aliyun OSS

The server supports OSS direct upload with presigned PUT URLs. Client and admin uploads go directly to OSS, while the worker downloads source files from OSS, processes them locally, then uploads generated models/audio back to OSS. The database stores public OSS URLs.

Use a public-read bucket directory or public-read bucket policy for the configured prefix:

```env
AIS_OSS_ENABLED=true
AIS_OSS_ENDPOINT=https://xxxx
AIS_OSS_INTERNAL_ENDPOINT=https://xxxx
AIS_OSS_BUCKET=xxxx
AIS_OSS_ACCESS_KEY_ID=xxxx
AIS_OSS_ACCESS_KEY_SECRET=xxxx
AIS_OSS_PUBLIC_BASE_URL=https://xxxx
AIS_OSS_KEY_PREFIX=ai-sing
AIS_OSS_UPLOAD_EXPIRE_SECONDS=900
```

`AIS_OSS_ENDPOINT` is used to generate presigned URLs for client/admin uploads. `AIS_OSS_INTERNAL_ENDPOINT` is used by the server container for faster intranet upload/download on Aliyun. If the container is not running inside the same Aliyun region, set the internal endpoint to the normal public endpoint.

### Build The Local Image In 1Panel

1. Stop the old Python runtime instance.
2. Open `Containers -> Images -> Build Image` in 1Panel.
3. Select this Dockerfile:

```text
/home/1panelProject/python/ai-sing-server/Dockerfile
```

4. Set the image name and tag to:

```text
ai-sing-server:local
```

5. Start the image build and wait until the image list contains `ai-sing-server:local`.

The first image build installs the dependencies and can take a long time. Regular container restarts do not install them again. Only build this image again after changing `requirements.txt`, `Dockerfile`, or server source files.

If Docker build downloads the PyTorch wheel too slowly, download the three GPU wheels manually and put them under `server/wheels/` before building. The Dockerfile installs local wheels first and only falls back to online download when no `.whl` files are present:

```text
server/wheels/torch-2.6.0+cu124-cp311-cp311-linux_x86_64.whl
server/wheels/torchaudio-2.6.0+cu124-cp311-cp311-linux_x86_64.whl
server/wheels/torchvision-0.21.0+cu124-cp311-cp311-linux_x86_64.whl
```

Download links:

```text
https://mirrors.aliyun.com/pytorch-wheels/cu124/torch-2.6.0%2Bcu124-cp311-cp311-linux_x86_64.whl
https://mirrors.aliyun.com/pytorch-wheels/cu124/torchaudio-2.6.0%2Bcu124-cp311-cp311-linux_x86_64.whl
https://mirrors.aliyun.com/pytorch-wheels/cu124/torchvision-0.21.0%2Bcu124-cp311-cp311-linux_x86_64.whl
```

Equivalent SSH build command:

```bash
cd /home/1panelProject/python/ai-sing-server
docker build -t ai-sing-server:local .
docker image ls ai-sing-server
```

The Dockerfile uses Tsinghua mirrors for both Debian packages and Debian security packages. It also separates Python installation into two steps:

- `requirements-gpu.txt` installs only CUDA-enabled PyTorch packages from the Aliyun PyTorch CUDA 12.4 mirror.
- `requirements.txt` installs the remaining API, RVC, and Demucs dependencies only from Tsinghua PyPI.

CUDA-enabled PyTorch is the one unavoidable official-source download for GPU training. If an unfinished earlier build is still waiting on `deb.debian.org`, cancel it, upload the current `Dockerfile`, `requirements-gpu.txt`, and `requirements.txt`, then build again. To temporarily override the Debian mirrors:

```bash
docker build \
  --build-arg DEBIAN_MIRROR=http://your-debian-mirror/debian \
  --build-arg DEBIAN_SECURITY_MIRROR=http://your-debian-security-mirror/debian-security \
  -t ai-sing-server:local .
```

### Create The Compose Service

Only after `ai-sing-server:local` exists locally:

1. Open `Containers -> Compose` in 1Panel.
2. Create a compose project using:

```text
/home/1panelProject/python/ai-sing-server/docker-compose.yml
```

3. Start the compose project.

The compose file sets `pull_policy: never`, because `ai-sing-server:local` is a local image built on this server and must not be pulled from Docker Hub.
It also sets `shm_size: "14gb"` for PyTorch/RVC data-loading workers. This avoids training failures such as `Unexpected bus error` or `No space left on device` under `/torch_*` when Docker's default shared-memory allocation is too small.

Equivalent SSH start commands:

```bash
cd /home/1panelProject/python/ai-sing-server
docker compose up -d
docker compose logs -f ai-sing-server
```

If you update only `docker-compose.yml`, you do not need to rebuild the image. Recreate the container so the new shared-memory allocation takes effect:

```bash
cd /home/1panelProject/python/ai-sing-server
docker compose up -d --force-recreate
docker exec ai-sing-server df -h /dev/shm
```

The final command should show a `14G` `/dev/shm` size before starting a new training job. In 1Panel, upload the updated `docker-compose.yml` and use the Compose project's recreate/rebuild-container operation rather than only restarting the existing container.

### Verify GPU

The Ubuntu host must have NVIDIA Container Toolkit configured for Docker. Verify that the host, Docker, and the running service can see the GPU:

```bash
nvidia-smi
docker run --rm --gpus all ubuntu nvidia-smi
docker exec ai-sing-server python - <<'PY'
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no cuda")
PY
```

The final command should print `True` and the RTX 4070 device name before you submit a training job.

If Compose reports `could not select device driver "nvidia" with capabilities: [[gpu]]`, first verify that the host driver works:

```bash
nvidia-smi
```

If that command displays the RTX 4070, install and configure NVIDIA Container Toolkit for Docker:

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends ca-certificates curl gnupg2

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
export NVIDIA_CONTAINER_TOOLKIT_VERSION=1.19.1-1
sudo apt-get install -y \
  nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
  nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
  libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
  libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION}

sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Then verify Docker GPU access before starting the Compose service:

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```

If `nvidia-smi` fails on the host itself, fix or install the NVIDIA driver before installing the container toolkit.

## Before First Upload

Verify the running service configuration and mounted RVC CLI:

```bash
docker exec ai-sing-server python - <<'PY'
from app.core.config import get_settings
s = get_settings()
print(s.database_url)
print(s.rvc_train_command)
print(s.demucs_command)
print(s.rvc_infer_command)
PY

docker exec ai-sing-server test -f /opt/rvc-cli/rvc_cli.py
docker exec ai-sing-server python -m demucs --help
docker exec ai-sing-server tail -f /app/logs/server.log
```

A short dry vocal sample is enough to prove that the task pipeline executes. A useful voice model requires a longer clean dry vocal recording.

### Training Progress And Model Files

For a voice-training task, the API output is written only after RVC has completed training, indexing, and final file copying. For task id `11`, the final files are:

```text
/home/1panelProject/python/ai-sing-server/data/outputs/models/11/model.pth
/home/1panelProject/python/ai-sing-server/data/outputs/models/11/model.index
```

RVC writes its working checkpoints first into the mounted RVC CLI directory:

```text
/opt/rvc-cli/logs/ai_sing_11/
```

If GPU usage becomes idle while a task is still running, inspect both places and the current training process:

```bash
docker exec ai-sing-server sh -lc 'ps -ef | grep -E "train_cli|rvc_cli|rvc/train/train" | grep -v grep || true'
docker exec ai-sing-server find /opt/rvc-cli/logs/ai_sing_11 -maxdepth 2 -type f -printf '%p\n' 2>/dev/null
find /home/1panelProject/python/ai-sing-server/data/outputs/models/11 -maxdepth 2 -type f -printf '%p\n' 2>/dev/null
```

The training adapter now emits live stage progress for preprocess, feature extraction, training, indexing, and final artifact copying, and the service streams RVC output to `logs/server.log`.

If training reaches `95%` and fails with `/opt/rvc-cli/assets/config.json` missing, the training checkpoints can usually be reused instead of recording audio again. For task id `13`, first repair the missing metadata configuration:

```bash
sudo mkdir -p /opt/rvc-cli/assets
printf '{\n  "model_author": "AI Sing"\n}\n' | sudo tee /opt/rvc-cli/assets/config.json
docker exec ai-sing-server sh -lc 'find /opt/rvc-cli/logs/ai_sing_13 /opt/rvc-cli/assets/weights -maxdepth 1 -type f \( -name "G_*.pth" -o -name "ai_sing_13*.pth" -o -name "*.index" \) -printf "%p\n" 2>/dev/null | sort'
docker exec ai-sing-server sh -lc 'cd /opt/rvc-cli && python - <<'"'"'PY'"'"'
import inspect
from rvc.train.process.extract_model import extract_model
print(inspect.signature(extract_model))
PY'
docker exec ai-sing-server sh -lc 'cd /opt/rvc-cli && grep -n -B 6 -A 16 "extract_model(" rvc/train/train.py | tail -n 50'
```

RVC CLI loads some bundled files through relative paths, so manual RVC operations must run with `/opt/rvc-cli` as the working directory. Some RVC CLI releases do not expose a `model_extract` command; in those releases recovery must call the internal `rvc.train.process.extract_model.extract_model(...)` function with the parameter shape used by the installed `rvc/train/train.py`.

For the installed signature `(ckpt, sr, name, model_path, epoch, step, hps, overtrain_info, vocoder, pitch_guidance=True, version='v2')`, recover task `13` without retraining:

```bash
docker exec ai-sing-server sh -lc 'cd /opt/rvc-cli && python - <<'"'"'PY'"'"'
import json
from pathlib import Path
from types import SimpleNamespace

import torch
from rvc.train.process.extract_model import extract_model

model_name = "ai_sing_13"
log_dir = Path("logs") / model_name
checkpoints = list(log_dir.glob("G_*.pth"))
checkpoint = max(checkpoints, key=lambda path: int(path.stem.split("_")[1]))
step = int(checkpoint.stem.split("_")[1])

def namespace(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{key: namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [namespace(item) for item in value]
    return value

hps = namespace(json.loads((log_dir / "config.json").read_text(encoding="utf-8")))
saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
weights = saved["model"] if isinstance(saved, dict) and "model" in saved else saved
output = log_dir / f"{model_name}_recovered.pth"
extract_model(
    ckpt=weights,
    sr="40k",
    name=model_name,
    model_path=str(output),
    epoch=200,
    step=step,
    hps=hps,
    overtrain_info={},
    vocoder="Default",
)
if not output.is_file():
    raise SystemExit("RVC model export did not write the recovered .pth file.")
print(f"Recovered model: {output.resolve()}")
PY'
```

After a successful extraction, copy the recovery artifacts into the server output directory:

```bash
docker exec ai-sing-server sh -lc '
mkdir -p /app/data/outputs/models/13
cp /opt/rvc-cli/logs/ai_sing_13/ai_sing_13_recovered.pth /app/data/outputs/models/13/model.pth
cp /opt/rvc-cli/logs/ai_sing_13/ai_sing_13.index /app/data/outputs/models/13/model.index
ls -lh /app/data/outputs/models/13
'
```

## Local Windows Development

For local development only, a Conda environment can still be used:

```powershell
conda env create -f environment.yml
conda activate ai-sing-server
python -m pip install -r requirements.txt
python start.py
```

The production 1Panel deployment does not use this Conda environment.

## Logs

The service writes task and command logs to:

```text
logs/server.log
```

When a task fails, check the client task error column, the database `jobs.error_message` field, and `logs/server.log` for the command output and stack trace.

## Test

Run from the repository root:

```powershell
$env:PYTHONPATH='server;client'
.\.venv\Scripts\python.exe -m pytest tests\server -v
```

