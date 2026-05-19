import sys
from pathlib import Path
from loguru import logger
import config

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stderr, level=config.LOG_LEVEL, colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}")
logger.add(LOG_DIR / "app_{time:YYYY-MM-DD}.log",
           rotation="1 day", retention="30 days", level="DEBUG")
