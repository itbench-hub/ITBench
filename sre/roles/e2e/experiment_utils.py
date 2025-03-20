import json
from pathlib import Path

import yaml


def load_yaml(config_path: Path):
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"File not found: {config_path}")
        raise
