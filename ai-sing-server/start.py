import argparse
import os

import uvicorn

from app.core.config import get_settings
from app.core.logging_config import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the AI Sing FastAPI server.")
    parser.add_argument("--host", default=os.getenv("AIS_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AIS_PORT", "8200")))
    parser.add_argument("--reload", action="store_true", default=os.getenv("AIS_RELOAD", "0") == "1")
    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_dir / "server.log", settings.log_level)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

