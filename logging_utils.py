from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


LOGS_ROOT = Path("logs")
LOGS_ROOT.mkdir(parents=True, exist_ok=True)


def create_run_dir(prefix: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = LOGS_ROOT / f"{timestamp}_{prefix}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def setup_logger(name: str, run_dir: Path) -> logging.Logger:
    logger = logging.getLogger(f"{name}_{run_dir.name}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(run_dir / "run.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2, default=str)
