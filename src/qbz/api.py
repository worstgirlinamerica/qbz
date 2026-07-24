"""Small native Qobuz API client used by qbz downloads."""

from __future__ import annotations

import hashlib
import base64
import os
import time

import requests
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from qbz.bundle import Bundle, DEFAULT_APP_ID


class QobuzClient:
    def __init__(self, app_id=None, token=None, secrets=None, session=None):
        self.session = session or requests.Session()
        self.app_id = str(app_id or os.getenv("QOBUZ_APP_ID") or "")
        self.secrets = list(secrets or ())
        self.session_id = None
        self.session_infos = None
        self.session_key = None
        if not self.app_id or not self.secrets:
            bundle = Bundle()
            if not self.app_id:
                self.app_id = bundle.get_app_id()
            if not self.secrets:
                self.secrets = list(bundle.get_secrets().values())
        if not self.app_id:
            self.app_id = DEFAULT_APP_ID
        self.sec = self.secrets[0] if self.secrets else None
        if not self.app_id:
            raise RuntimeError("Qobuz app ID is unavailable")
        if not self.secrets:
            raise RuntimeError("Qobuz request secrets are unavailable")
        self.session.headers.update({
            "X-App-Id": self.app_id,
            "X-User-Auth-Token": token or "",
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
        })

    @staticmethod
    def request_signature(track_id, quality_id, timestamp, secret):
        value = (
            f"trackgetFileUrlformat_id{quality_id}intentstreamtrack_id{track_id}"
            f"{timestamp}{secret}"
        )
        return hashlib.md5(value.encode("utf-8")).hexdigest()

    def get_track_url(self, track_id, quality_id):
        quality_id = str(quality_id)
        if quality_id not in {"5", "6", "7", "27"}:
            raise ValueError("quality_id must be one of 5, 6, 7, or 27")
        timestamp = int(time.time())
        url = "https://www.qobuz.com/api.json/0.2/track/getFileUrl"
        response = None
        for secret in self.secrets:
            response = self.session.get(
                url,
                params={
                    "app_id": self.app_id,
                    "track_id": track_id,
                    "format_id": quality_id,
                    "intent": "stream",
                    "request_ts": timestamp,
                    "request_sig": self.request_signature(track_id, quality_id, timestamp, secret),
                },
                timeout=30,
            )
            if response.status_code != 400:
                break
        if response.status_code < 400:
            response.raise_for_status()
            return response.json()
        if quality_id == "5":
            response.raise_for_status()
        return self.get_segmented_url(track_id, quality_id)

    @staticmethod
    def _b64url_decode(value):
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    def _modern_signature(self, endpoint, params, secret):
        object_name, method = endpoint.split("/")
        values = [object_name, method]
        for key in sorted(params):
            if key not in {"request_ts", "request_sig"}:
                value = params[key]
                if isinstance(value, (str, int, float)):
                    values.extend((key, str(value)))
        values.extend((str(params["request_ts"]), secret))
        return hashlib.md5("".join(values).encode("utf-8")).hexdigest()

    def _start_session(self):
        timestamp = int(time.time())
        params = {"profile": "qbz-1", "request_ts": timestamp}
        params["request_sig"] = self._modern_signature("session/start", params, self.sec)
        response = self.session.post(
            "https://www.qobuz.com/api.json/0.2/session/start",
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        self.session_id = payload["session_id"]
        self.session_infos = payload["infos"]
        salt, info = self.session_infos.split(".")
        self.session_key = HKDF(
            algorithm=hashes.SHA256(),
            length=16,
            salt=self._b64url_decode(salt),
            info=self._b64url_decode(info),
        ).derive(bytes.fromhex(self.sec))
        self.session.headers.update({"X-Session-Id": self.session_id})

    def get_segmented_url(self, track_id, quality_id):
        if self.session_id is None:
            self._start_session()
        timestamp = int(time.time())
        params = {
            "track_id": track_id,
            "format_id": quality_id,
            "intent": "import",
            "request_ts": timestamp,
        }
        params["request_sig"] = self._modern_signature("file/url", params, self.sec)
        response = self.session.get(
            "https://www.qobuz.com/api.json/0.2/file/url", params=params, timeout=30
        )
        response.raise_for_status()
        payload = response.json()
        if "bits_depth" in payload and "bit_depth" not in payload:
            payload["bit_depth"] = payload["bits_depth"]
        if payload.get("sampling_rate", 0) > 1000:
            payload["sampling_rate"] /= 1000
        key_token = payload.get("key")
        if key_token:
            _, wrapped, iv = key_token.split(".")
            decryptor = Cipher(
                algorithms.AES(self.session_key), modes.CBC(self._b64url_decode(iv))
            ).decryptor()
            padded = decryptor.update(self._b64url_decode(wrapped)) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            payload["raw_key"] = unpadder.update(padded) + unpadder.finalize()
        return payload
