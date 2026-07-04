"""Mocasus Temp-Mail API Provider.
API endpoint: POST https://mocasus.my.id/api/temp-mail
Auth: x-api-key header
"""
import requests
import time
from .base import EmailProvider, Inbox

class MocasusProvider(EmailProvider):
    """Mocasus.my.id disposable email service."""

    name = "mocasus"
    BASE = "https://mocasus.my.id/api/temp-mail"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "MorphWorker/1.0"
        })

    def create_inbox(self, username: str = None) -> Inbox:
        """Create a new temp-mail inbox."""
        payload = {}
        if username:
            payload["username"] = username

        r = self.session.post(f"{self.BASE}/create", json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()

        email = data.get("email") or data.get("address") or data.get("data", {}).get("email")
        if not email:
            raise RuntimeError(f"Failed to parse email from response: {data}")

        return Inbox(
            email=email,
            password=data.get("password", ""),
            provider="mocasus",
            meta={
                "id": data.get("id"),
                "token": data.get("token") or data.get("owner_token"),
            }
        )

    def wait_for_code(self, inbox: Inbox, timeout: int = 120, code_length: int = 6) -> str:
        """Poll for verification code."""
        return self._poll_loop(inbox, timeout, poll_interval=3.0, code_length=code_length)

    def get_messages(self, inbox: Inbox) -> list[dict]:
        """Get inbox messages."""
        try:
            r = self.session.get(f"{self.BASE}/messages", params={"email": inbox.email}, timeout=10)
            r.raise_for_status()
            data = r.json()
            # API may return {messages: [...]} or {data: [...]} or just [...]
            if isinstance(data, list):
                return data
            return data.get("messages") or data.get("data") or []
        except Exception:
            return []

    def delete_inbox(self, inbox: Inbox) -> bool:
        """Delete inbox."""
        try:
            r = self.session.delete(f"{self.BASE}/delete", json={"email": inbox.email}, timeout=10)
            return r.status_code == 200
        except Exception:
            return False
