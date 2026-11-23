import sys
from pathlib import Path

from loguru import logger

LOG_FILE = Path(__file__).resolve().parent.parent / "runs" / "bot.log"


def setup_logging() -> None:
    """Short INFO, all DEBUG goes to runs/bot.log"""
    logger.remove()
    logger.add(
        sys.stderr, level="INFO", format="{time:HH:mm:ss.SSS} {level: <7} {message}"
    )
    logger.add(LOG_FILE, level="DEBUG", mode="w")
