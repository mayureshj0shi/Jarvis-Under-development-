from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

_CONFIG = None
_BASE_DIR = Path(__file__).resolve().parent.parent


def load_config():
    global _CONFIG
    load_dotenv(_BASE_DIR / ".env")
    cfg_path = _BASE_DIR / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        _CONFIG = yaml.safe_load(f)
    return _CONFIG


def get_config():
    if _CONFIG is None:
        load_config()
    return _CONFIG


def base_dir():
    return _BASE_DIR
