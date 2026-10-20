import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.routers import youtube
from app.services import youtube_service


class FakeStartFlow:
    def authorization_url(self, **_kwargs):
        return "https://accounts.example/authorize", "test-state"


class OAuthFlowTests(unittest.TestCase):
    def test_oauth_start_persists_verifier_for_its_state(self):
        with tempfile.TemporaryDirectory() as directory:
            pending_path = Path(directory) / "oauth_pending.json"
            captured = {}

            def make_flow(**kwargs):
                captured.update(kwargs)
                return FakeStartFlow()

            with patch.object(youtube_service, "backend_path", lambda _value: pending_path), patch.object(
                youtube_service, "make_flow", make_flow
            ):
                self.assertEqual(
                    youtube_service.start_oauth_authorization(), "https://accounts.example/authorize"
                )
                verifier = youtube_service.consume_oauth_verifier("test-state")

            self.assertEqual(verifier, captured["code_verifier"])
            self.assertGreaterEqual(len(verifier), 43)
            self.assertLessEqual(len(verifier), 128)
            with patch.object(youtube_service, "backend_path", lambda _value: pending_path):
                self.assertIsNone(youtube_service.consume_oauth_verifier("test-state"))

    def test_callback_uses_the_persisted_verifier(self):
        captured = {}

        class FakeCallbackFlow:
            credentials = object()

            def fetch_token(self, **kwargs):
                captured["fetch_token"] = kwargs

        with patch.object(youtube_service, "consume_oauth_verifier", lambda state: "saved-verifier"), patch.object(
            youtube_service,
            "make_flow",
            lambda **kwargs: captured.update(kwargs) or FakeCallbackFlow(),
        ), patch.object(youtube_service, "save_credentials", lambda _credentials: None):
            response = youtube.oauth_callback(state="valid-state", code="authorization-code")

        self.assertEqual(response.status_code, 307)
        self.assertEqual(captured["state"], "valid-state")
        self.assertEqual(captured["code_verifier"], "saved-verifier")
        self.assertEqual(captured["fetch_token"], {"code": "authorization-code"})

    def test_callback_rejects_missing_or_expired_state(self):
        with patch.object(youtube_service, "consume_oauth_verifier", lambda state: None):
            with self.assertRaises(HTTPException) as raised:
                youtube.oauth_callback(state="expired-state", code="authorization-code")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("expired", raised.exception.detail)
