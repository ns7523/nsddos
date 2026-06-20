"""Central logging configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

from nsddos.constants import LOG_DIR
from nsddos.config import ensure_runtime_directories


def setup_logging(level: str = "INFO") -> Path:
    """Configure console and rotating file logging."""
    resolved_level = os.getenv("NSDDOS_LOG_LEVEL", level).upper()
    ensure_runtime_directories()
    log_file = LOG_DIR / "nsddos.log"

    logger.remove()
    logger.add(
        sys.stderr,
        level=resolved_level,
        colorize=True,
        enqueue=False,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
    )
    logger.add(
        log_file,
        level=resolved_level,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} | {message}",
    )
    return log_file
