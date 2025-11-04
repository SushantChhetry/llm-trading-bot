"""Configuration settings for the trading bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path("/app")
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Minimal config class - most values come from environment variables
class Config:
    DATA_DIR = DATA_DIR
    LOG_DIR = LOG_DIR

config = Config()
