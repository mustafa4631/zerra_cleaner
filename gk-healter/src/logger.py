"""
GK Healter – Centralized Logging Configuration

Provides structured logging with file and console output.
Uses Python's standard logging module for professional log management.
"""

import os
import logging
import logging.handlers
from typing import Optional

# Application-wide log directory
LOG_DIR = os.path.expanduser("~/.local/share/gk-healter/logs")
LOG_FILE = os.path.join(LOG_DIR, "gk-healter.log")
MAX_LOG_SIZE = 2 * 1024 * 1024  # 2 MB
BACKUP_COUNT = 3


def setup_logging(level: Optional[int] = None) -> logging.Logger:
    """
    Initialize application-wide logging.

    Args:
        level: Logging level (default: INFO).

    Returns:
        Root application logger.
    """
    if level is None:
        level = logging.INFO

    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)

    # Root logger for the application
    logger = logging.getLogger("gk-healter")
    logger.setLevel(level)

    # Prevent duplicate handlers on re-init
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── File handler (rotating) ───────────────────────────────────────────
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass  # Can't write log file, continue with console only

    # ── Console handler ───────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("GK Healter logging initialized (level=%s)", logging.getLevelName(level))
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the application namespace."""
    return logging.getLogger(f"gk-healter.{name}")
