"""
AI Cinematic Story Narrator
Configuration loader utility.
"""

from pathlib import Path
import yaml


def load_config(config_path: str = "config/settings.yaml") -> dict:
    """Load settings from a yaml configuration file."""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
