FROM python:3.11-slim-bookworm

ARG DEBIAN_MIRROR=http://mirrors.aliyun.com/debian
ARG DEBIAN_SECURITY_MIRROR=http://mirrors.aliyun.com/debian-security
ARG DEBUG_GPU_DOWNLOAD=0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    HF_HUB_DISABLE_XET=1

WORKDIR /app

RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i "s|http://deb.debian.org/debian$|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
        sed -i "s|http://deb.debian.org/debian-security$|${DEBIAN_SECURITY_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && if [ -f /etc/apt/sources.list ]; then \
        sed -i "s|http://deb.debian.org/debian |${DEBIAN_MIRROR} |g" /etc/apt/sources.list; \
        sed -i "s|http://deb.debian.org/debian-security |${DEBIAN_SECURITY_MIRROR} |g" /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ffmpeg \
        git \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsamplerate0-dev \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY constraints-gpu.txt /tmp/constraints-gpu.txt
COPY requirements-gpu.txt /tmp/requirements-gpu.txt
COPY wheels /tmp/wheels
RUN if [ "$DEBUG_GPU_DOWNLOAD" = "1" ]; then \
        echo "=== /tmp/requirements-gpu.txt ==="; \
        cat /tmp/requirements-gpu.txt; \
        echo "=== /tmp/wheels ==="; \
        find /tmp/wheels -maxdepth 1 -type f -name "*.whl" -printf "%f\n" || true; \
        echo "=== pip config ==="; \
        python -m pip config list || true; \
        echo "=== curl aliyun torch headers ==="; \
        curl -I -L --connect-timeout 20 --max-time 60 "https://mirrors.aliyun.com/pytorch-wheels/cu124/torch-2.6.0%2Bcu124-cp311-cp311-linux_x86_64.whl"; \
    fi
RUN python -m pip install --upgrade pip \
    && if ls /tmp/wheels/*.whl >/dev/null 2>&1; then \
        python -m pip install -v /tmp/wheels/*.whl; \
    else \
        mkdir -p /tmp/wheels-download \
        && curl -4 -L --fail --retry 5 --retry-delay 2 \
            -o /tmp/wheels-download/torch-2.6.0+cu124-cp311-cp311-linux_x86_64.whl \
            "https://mirrors.aliyun.com/pytorch-wheels/cu124/torch-2.6.0%2Bcu124-cp311-cp311-linux_x86_64.whl" \
        && curl -4 -L --fail --retry 5 --retry-delay 2 \
            -o /tmp/wheels-download/torchaudio-2.6.0+cu124-cp311-cp311-linux_x86_64.whl \
            "https://mirrors.aliyun.com/pytorch-wheels/cu124/torchaudio-2.6.0%2Bcu124-cp311-cp311-linux_x86_64.whl" \
        && curl -4 -L --fail --retry 5 --retry-delay 2 \
            -o /tmp/wheels-download/torchvision-0.21.0+cu124-cp311-cp311-linux_x86_64.whl \
            "https://mirrors.aliyun.com/pytorch-wheels/cu124/torchvision-0.21.0%2Bcu124-cp311-cp311-linux_x86_64.whl" \
        && python -m pip install -v /tmp/wheels-download/*.whl; \
    fi

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements.txt -c /tmp/constraints-gpu.txt

RUN if ls /tmp/wheels/*.whl >/dev/null 2>&1; then \
        python -m pip install --force-reinstall --no-deps -v /tmp/wheels/*.whl; \
    else \
        python -m pip install --force-reinstall --no-deps -v /tmp/wheels-download/*.whl; \
    fi \
    && python -m pip show torch torchaudio torchvision \
    && python -c "import torch, torchaudio, torchcrepe; print('torch=' + torch.__version__); print('cuda=' + str(torch.version.cuda)); print('torchaudio=' + torchaudio.__version__); print('torchcrepe=ok')"

COPY app ./app
COPY scripts ./scripts
COPY start.py ./start.py

EXPOSE 8200

CMD ["python", "start.py"]

