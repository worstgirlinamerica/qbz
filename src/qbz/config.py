"""User-editable qbz configuration."""

from __future__ import annotations

import configparser
import os
from pathlib import Path

from platformdirs import user_config_path


CONFIG_PATH = Path(os.getenv("QBZ_CONFIG_FILE", "")).expanduser() if os.getenv("QBZ_CONFIG_FILE") else user_config_path("qbz") / "config.ini"

DEFAULTS = {
    "download": {
        "quality": "27",
        "output_dir": str(Path.home() / "Qobuz"),
        "country": "",
        "write_credits": "false",
    },
    "display": {
        "show_email": "false",
    },
    "auth": {
        "token_file": "",
        "app_id": "",
    },
    "links": {
        "track_template": "https://play.qobuz.com/track/{track_id}",
    },
}


def load():
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(CONFIG_PATH, encoding="utf-8")
    return parser


def get(section, option, fallback=None):
    parser = load()
    return parser.get(section, option, fallback=fallback)


def getboolean(section, option, fallback=False):
    parser = load()
    return parser.getboolean(section, option, fallback=fallback)


def make_default():
    parser = configparser.ConfigParser(interpolation=None)
    for section, values in DEFAULTS.items():
        parser[section] = values
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        parser.write(handle)
    return CONFIG_PATH
