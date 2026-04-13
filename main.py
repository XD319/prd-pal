import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from prd_pal.utils.logging import build_formatter, setup_logging

load_dotenv()

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

setup_logging()

file_handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
file_handler.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").strip().upper(), logging.INFO))
file_handler.setFormatter(build_formatter(os.getenv("LOG_FORMAT", "human")))
logging.getLogger().addHandler(file_handler)

# Create logger instance
logger = logging.getLogger(__name__)

from prd_pal.server.app import app

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

