import logging
from pathlib import Path


def configure_logging(log_file: Path | str, level: str = "INFO") -> None:
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(str(path), encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
