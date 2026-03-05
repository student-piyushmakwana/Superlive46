import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import coloredlogs

# Define the log structure
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Resolve path smoothly directly to root folder
LOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(LOG_DIR, "superlive.log")

def setup_logger():
    """
    Configures and returns the central logging instance for the application.
    Implements rotating file handler to prevent massive log dumps.
    """
    root_logger = logging.getLogger()
    
    # If handlers already exist (e.g., hot reloads), clear them to avoid duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.setLevel(logging.INFO)

    # 1. File Handler (Rotating log up to 5MB, keep 2 backups)
    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # 2. Console Handler with Colors
    coloredlogs.install(
        level="INFO",
        logger=root_logger,
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
        level_styles={
            'info': {'color': 'green'},
            'notice': {'color': 'magenta'},
            'verbose': {'color': 'blue'},
            'success': {'color': 'green', 'bold': True},
            'spam': {'color': 'cyan'},
            'critical': {'color': 'red', 'bold': True},
            'error': {'color': 'red'},
            'debug': {'color': 'white', 'faint': True},
            'warning': {'color': 'yellow'}
        },
        field_styles={
            'asctime': {'color': 'white', 'faint': True},
            'levelname': {'color': 'cyan', 'bold': True},
            'name': {'color': 'blue'}
        }
    )

    # Silence verbose third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("hypercorn").setLevel(logging.WARNING)

    return root_logger

# Initialize on import
logger = setup_logger()
