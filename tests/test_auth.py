import base64
import hashlib
import unittest

from qbz.api import QobuzClient
from qbz.bundle import Bundle


class Response:
    def __init__(self, text="", status_code=200, payload=None):
        self.text = text
        self.status_code = status_code
        self._payload = payload or {"url": "https://cdn.example/file.flac"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)

    def json(self):
        return self._payload


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.headers = {}
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


class AuthTests(unittest.TestCase):
    def test_bundle_extracts_app_id_and_secret(self):
        secret = "test-secret"
        encoded = base64.b64encode(secret.encode()).decode() + ("x" * 44)
        page = '<script src="/resources/1.2.3-a123/bundle.js"></script>'
        bundle = 'production:{api:{appId:"123456789",appSecret:"' + ("x" * 32) + '"}} '
        bundle += f'x.initialSeed("{encoded}",window.utimezone.utc)'
        session = Session([Response(page), Response(bundle)])

        parsed = Bundle(session=session)

        self.assertEqual(parsed.get_app_id(), "123456789")
        self.assertEqual(list(parsed.get_secrets().values()), [secret])
        self.assertTrue(session.calls[1][0].endswith("/resources/1.2.3-a123/bundle.js"))

    def test_track_url_uses_qobuz_signature(self):
        session = Session([Response(payload={"url": "https://cdn.example/a.flac"})])
        client = QobuzClient(app_id="123456789", token="token", secrets=["secret"], session=session)

        # Freeze the timestamp without touching the network or global clock.
        import qbz.api
        original = qbz.api.time.time
        qbz.api.time.time = lambda: 1700000000
        try:
            result = client.get_track_url("42", "27")
        finally:
            qbz.api.time.time = original

        params = session.calls[0][1]["params"]
        expected = hashlib.md5(
            b"trackgetFileUrlformat_id27intentstreamtrack_id421700000000secret"
        ).hexdigest()
        self.assertTrue(result["url"].endswith("a.flac"))
        self.assertEqual(params["request_sig"], expected)
        self.assertEqual(session.calls[0][1]["timeout"], 30)
