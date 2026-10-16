import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Sing adapter for RVC CLI training.")
    parser.add_argument("--input", required=True, help="Input dry vocal audio file.")
    parser.add_argument("--output-dir", required=True, help="Directory where model.pth and model.index are written.")
    parser.add_argument("--job-id", required=True, help="AI Sing job id, used as RVC model name.")
    parser.add_argument("--rvc-root", default=os.getenv("RVC_CLI_ROOT", "/opt/rvc-cli"))
    parser.add_argument("--rvc-python", default=os.getenv("RVC_PYTHON", "/opt/rvc-cli/venv/bin/python"))
    parser.add_argument("--sample-rate", type=int, default=int(os.getenv("RVC_SAMPLE_RATE", "40000")))
    parser.add_argument("--epochs", type=int, default=int(os.getenv("RVC_EPOCHS", "200")))
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("RVC_BATCH_SIZE", "8")))
    parser.add_argument("--save-every-epoch", type=int, default=int(os.getenv("RVC_SAVE_EVERY_EPOCH", "10")))
    parser.add_argument("--gpu", default=os.getenv("RVC_GPU", "0"))
    parser.add_argument("--cpu-cores", type=int, default=int(os.getenv("RVC_CPU_CORES", "4")))
    parser.add_argument("--include-mutes", type=int, default=int(os.getenv("RVC_INCLUDE_MUTES", "2")))
    parser.add_argument(
        "--cut-preprocess",
        choices=("Skip", "Simple", "Automatic"),
        default=os.getenv("RVC_CUT_PREPROCESS", "Automatic"),
    )
    args = parser.parse_args()

    source = Path(args.input).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Input audio missing: {source}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rvc_root = Path(args.rvc_root).resolve()
    rvc_cli = rvc_root / "rvc_cli.py"
    if not rvc_cli.is_file():
        raise FileNotFoundError(f"RVC CLI entrypoint missing: {rvc_cli}")
    ensure_rvc_export_config(rvc_root)
    check_rvc_python_environment(args.rvc_python, rvc_root)

    model_name = f"ai_sing_{args.job_id}"
    dataset_dir = output_dir / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    dataset_audio = dataset_dir / f"voice{source.suffix or '.wav'}"
    shutil.copy2(source, dataset_audio)

    print("AIS_PROGRESS=15", flush=True)
    run(
        args.rvc_python,
        rvc_cli,
        build_preprocess_args(
            model_name,
            str(dataset_dir),
            args.sample_rate,
            args.cpu_cores,
            args.cut_preprocess,
        ),
        cwd=rvc_root,
    )
    print("AIS_PROGRESS=25", flush=True)
    run(
        args.rvc_python,
        rvc_cli,
        build_extract_args(model_name, args.sample_rate, args.gpu, args.cpu_cores, args.include_mutes),
        cwd=rvc_root,
    )
    require_extract_outputs(rvc_root, model_name)
    print("AIS_PROGRESS=40", flush=True)
    run(
        args.rvc_python,
        rvc_cli,
        build_train_args(
            model_name,
            args.sample_rate,
            args.gpu,
            args.epochs,
            args.batch_size,
            args.save_every_epoch,
        ),
        cwd=rvc_root,
        total_epochs=args.epochs,
    )
    print("AIS_PROGRESS=85", flush=True)
    run(
        args.rvc_python,
        rvc_cli,
        build_index_args(model_name),
        cwd=rvc_root,
    )

    print("AIS_PROGRESS=95", flush=True)
    pth = newest_file(rvc_root, f"*{model_name}*.pth")
    index = newest_file(rvc_root, f"*{model_name}*.index")
    if pth is None:
        raise FileNotFoundError(f"RVC training finished but no .pth was found for model {model_name}")
    if index is None:
        raise FileNotFoundError(f"RVC index finished but no .index was found for model {model_name}")

    shutil.copy2(pth, output_dir / "model.pth")
    shutil.copy2(index, output_dir / "model.index")
    (output_dir / "rvc_train_manifest.txt").write_text(
        "\n".join(
            [
                f"model_name={model_name}",
                f"source={source}",
                f"dataset={dataset_dir}",
                f"rvc_root={rvc_root}",
                f"source_pth={pth}",
                f"source_index={index}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output_dir / 'model.pth'}")
    print(f"Wrote {output_dir / 'model.index'}")
    return 0


def run(python_bin: str, rvc_cli: Path, args: list[str], cwd: Path, total_epochs: int = 1) -> None:
    command = [python_bin, "-u", str(rvc_cli), *args]
    print("Running:", " ".join(command), flush=True)
    is_train = len(args) > 0 and args[0] == "train"
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if process.stdout:
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            if is_train and "epoch=" in line:
                m = re.search(r"epoch=(\d+)", line)
                if m:
                    ep = int(m.group(1))
                    if total_epochs > 0:
                        prog = min(84, int(40 + (ep / total_epochs) * 45))
                        print(f"AIS_PROGRESS={prog}", flush=True)
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError(f"Command failed with exit code {returncode}: {' '.join(command)}")


def check_rvc_python_environment(python_bin: str, cwd: Path) -> None:
    check_code = (
        "import torch, torchaudio, torchcrepe\n"
        "print('torch=' + torch.__version__)\n"
        "print('cuda=' + str(torch.version.cuda))\n"
        "print('torchaudio=' + torchaudio.__version__)\n"
        "print('torchcrepe=ok')\n"
    )
    result = subprocess.run(
        [python_bin, "-c", check_code],
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
    )
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
    if output:
        print(output, flush=True)
    if result.returncode != 0:
        raise RuntimeError(
            "RVC Python environment check failed before training. "
            "The most common cause is incompatible torch/torchaudio wheels. "
            "Install matching torch, torchaudio and torchvision CUDA builds.\n"
            f"{output}"
        )


def require_extract_outputs(rvc_root: Path, model_name: str) -> None:
    experiment_dir = rvc_root / "logs" / model_name
    config_path = experiment_dir / "config.json"
    extracted_dir = experiment_dir / "extracted"
    has_features = extracted_dir.is_dir() and any(path.is_file() for path in extracted_dir.rglob("*"))
    if config_path.is_file() and has_features:
        return
    missing = []
    if not config_path.is_file():
        missing.append(str(config_path))
    if not has_features:
        missing.append(str(extracted_dir))
    raise RuntimeError(
        "RVC feature extraction failed: expected feature files were not created. "
        "Check the extract-stage logs above; if torchaudio reports an undefined symbol, "
        "torch and torchaudio are installed with incompatible versions. Missing: "
        + ", ".join(missing)
    )


def ensure_rvc_export_config(rvc_root: Path) -> Path:
    config_path = rvc_root / "assets" / "config.json"
    if config_path.exists():
        return config_path
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"model_author": "AI Sing"}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created missing RVC export config: {config_path}", flush=True)
    return config_path


def build_preprocess_args(
    model_name: str,
    dataset_path: str,
    sample_rate: int,
    cpu_cores: int,
    cut_preprocess: str,
) -> list[str]:
    return [
        "preprocess",
        "--model_name",
        model_name,
        "--dataset_path",
        dataset_path,
        "--sample_rate",
        str(sample_rate),
        "--cpu_cores",
        str(cpu_cores),
        "--cut_preprocess",
        cut_preprocess,
    ]


def build_extract_args(
    model_name: str,
    sample_rate: int,
    gpu: str,
    cpu_cores: int,
    include_mutes: int,
) -> list[str]:
    return [
        "extract",
        "--model_name",
        model_name,
        "--f0_method",
        "rmvpe",
        "--sample_rate",
        str(sample_rate),
        "--gpu",
        str(gpu),
        "--cpu_cores",
        str(cpu_cores),
        "--include_mutes",
        str(include_mutes),
    ]


def build_train_args(
    model_name: str,
    sample_rate: int,
    gpu: str,
    epochs: int,
    batch_size: int,
    save_every_epoch: int,
) -> list[str]:
    return [
        "train",
        "--model_name",
        model_name,
        "--save_every_epoch",
        str(save_every_epoch),
        "--total_epoch",
        str(epochs),
        "--sample_rate",
        str(sample_rate),
        "--batch_size",
        str(batch_size),
        "--gpu",
        str(gpu),
    ]


def build_index_args(model_name: str) -> list[str]:
    return ["index", "--model_name", model_name, "--index_algorithm", "Auto"]


def newest_file(root: Path, pattern: str) -> Path | None:
    matches = [path for path in root.rglob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


if __name__ == "__main__":
    raise SystemExit(main())
