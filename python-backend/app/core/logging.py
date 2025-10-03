from loguru import logger
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger.remove()
logger.add(lambda m: print(m, end=""), level=LOG_LEVEL)

__all__ = ["logger"]

