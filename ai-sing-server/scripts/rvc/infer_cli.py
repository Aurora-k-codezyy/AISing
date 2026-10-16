import argparse
import os
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Sing adapter for RVC CLI inference.")
    parser.add_argument("--input", required=True, help="Input vocals wav file.")
    parser.add_argument("--model", required=True, help="RVC model .pth file.")
    parser.add_argument("--output", required=True, help="Output AI vocal wav path.")
    parser.add_argument("--index", default="", help="Optional RVC .index path. Defaults to sibling model.index.")
    parser.add_argument("--rvc-root", default=os.getenv("RVC_CLI_ROOT", "/opt/rvc-cli"))
    parser.add_argument("--rvc-python", default=os.getenv("RVC_PYTHON", "/opt/rvc-cli/venv/bin/python"))
    parser.add_argument("--pitch", type=int, default=int(os.getenv("RVC_PITCH", "0")))
    parser.add_argument("--index-rate", type=float, default=float(os.getenv("RVC_INDEX_RATE", "0.3")))
    parser.add_argument("--f0-method", default=os.getenv("RVC_F0_METHOD", "rmvpe"))
    args = parser.parse_args()

    input_path = require_file(args.input, "Input vocals")
    model_path = require_file(args.model, "RVC model")
    index_path = resolve_required_index(model_path, args.index)

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rvc_root = Path(args.rvc_root).resolve()
    rvc_cli = require_file(rvc_root / "rvc_cli.py", "RVC CLI entrypoint")

    command = [
        args.rvc_python,
        str(rvc_cli),
        "infer",
        "--pitch",
        str(args.pitch),
        "--input_path",
        str(input_path),
        "--output_path",
        str(output_path),
        "--pth_path",
        str(model_path),
        "--index_path",
        str(index_path),
        "--index_rate",
        str(args.index_rate),
        "--f0_method",
        args.f0_method,
        "--export_format",
        "WAV",
    ]
    print("Running:", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=str(rvc_root), check=False, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")
    require_file(output_path, "RVC inference output")
    print(f"Wrote {output_path}")
    return 0


def require_file(path: str | Path, label: str) -> Path:
    target = Path(path).resolve()
    if not target.is_file():
        raise FileNotFoundError(f"{label} missing: {target}")
    return target


def resolve_required_index(model_path: Path, index: str) -> Path:
    if index:
        return require_file(Path(index).resolve(), "RVC index")
    candidates = [
        model_path.with_name("model.index"),
        model_path.with_suffix(".index"),
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    indexes = list(model_path.parent.glob("*.index"))
    if indexes:
        return indexes[0]
    return require_file(model_path.with_name("model.index"), "RVC index")


if __name__ == "__main__":
    raise SystemExit(main())
