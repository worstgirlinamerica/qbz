"""Runtime extraction of the Qobuz web-player app configuration."""

from __future__ import annotations

import base64
import re
from collections import OrderedDict
from dataclasses import dataclass

import requests

BASE_URL = "https://play.qobuz.com"
# The browser app ID and a browser-auth token are not always interchangeable.
# Keep the known qbz-compatible public ID as the fallback; users can override
# it with QOBUZ_APP_ID while bundle secrets remain dynamic.
DEFAULT_APP_ID = "798273057"
_BUNDLE_URL_REGEX = re.compile(r'<script[^>]+src="(?P<path>/resources/[^"?]+/bundle\.js)[^>]*>', re.I)
_APP_ID_REGEX = re.compile(
    r'production:\{api:\{appId:"(?P<app_id>\d{9})",appSecret:"[A-Za-z0-9]{32}"'
)
_SEED_REGEX = re.compile(r'[a-z]\.initialSeed\("(?P<seed>[\w=]+)",window\.utimezone\.(?P<timezone>[a-z]+)\)')


@dataclass(frozen=True)
class WebConfig:
    app_id: str
    secrets: tuple[str, ...] = ()


class Bundle:
    """Fetch and parse the current public Qobuz web-player bundle."""

    def __init__(self, session=None, timeout=20):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.session.headers.setdefault("User-Agent", "Mozilla/5.0 (qbz)")
        page = self.session.get(f"{BASE_URL}/login", timeout=timeout)
        page.raise_for_status()
        match = _BUNDLE_URL_REGEX.search(page.text)
        if not match:
            raise RuntimeError("Could not find the Qobuz web-player bundle URL")
        bundle = self.session.get(BASE_URL + match.group("path"), timeout=timeout)
        bundle.raise_for_status()
        self._bundle = bundle.text

    def get_app_id(self):
        match = _APP_ID_REGEX.search(self._bundle)
        if not match:
            raise RuntimeError("Could not find the Qobuz app ID in the web-player bundle")
        return match.group("app_id")

    def get_secrets(self):
        grouped = OrderedDict()
        for match in _SEED_REGEX.finditer(self._bundle):
            grouped.setdefault(match.group("timezone"), [match.group("seed")])
        if len(grouped) > 1:
            grouped.move_to_end(list(grouped)[1], last=False)
        zones = "|".join(zone.capitalize() for zone in grouped)
        if zones:
            extras = re.compile(rf'name:"\w+/(?P<timezone>{zones})",info:"(?P<info>[\w=]+)",extras:"(?P<extras>[\w=]+)"')
            for match in extras.finditer(self._bundle):
                grouped.setdefault(match.group("timezone").lower(), []).extend([match.group("info"), match.group("extras")])
        decoded = OrderedDict()
        for zone, parts in grouped.items():
            try:
                decoded[zone] = base64.standard_b64decode("".join(parts)[:-44]).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                continue
        return decoded

    def config(self):
        return WebConfig(self.get_app_id(), tuple(self.get_secrets().values()))


def get_app_id():
    return Bundle().get_app_id()
