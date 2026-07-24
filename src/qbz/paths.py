"""Portable qbz user-data locations."""

import os
from pathlib import Path

from platformdirs import user_config_path


def token_path():
    configured = os.getenv("QBZ_TOKEN_FILE", "").strip()
    return Path(configured).expanduser() if configured else user_config_path("qbz") / "token"


def configured_token_path():
    from qbz.config import get

    configured = os.getenv("QBZ_TOKEN_FILE", "").strip() or get("auth", "token_file", "")
    return Path(configured).expanduser() if configured else user_config_path("qbz") / "token"


def output_path():
    from qbz.config import get

    configured = os.getenv("QBZ_OUTPUT_DIR", "").strip() or get("download", "output_dir", str(Path.home() / "Qobuz"))
    return Path(configured).expanduser()
