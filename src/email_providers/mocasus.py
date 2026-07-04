"""Mocasus Temp-Mail API v2 Provider.
Base: Supabase Edge Function — query-param actions
Auth: x-api-key header
Docs: https://mocasus.my.id/docs-temp
"""
import requests
import time
from .base import EmailProvider, Inbox


class MocasusProvider(EmailProvider):
    """Mocasus.my.id disposable email service — v2 Supabase Edge Function."""

    name = "mocasus"
    BASE = "https://ijrccpgiulrmfpavazsl.supabase.co/functions/v1/temp-mail-api-v2"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": api_key,
            "User-Agent": "MorphWorker/1.0",
        })

    def create_inbox(self, username: str = None) -> Inbox:
        """Create a new temp-mail inbox via v2 API.

        POST ?action=create
        Returns: {address, owner_token, domain, expires_at, tier}
        """
        payload = {}
        if username:
            payload["username"] = username

        r = self.session.post(
            self.BASE,
            params={"action": "create"},
            json=payload or None,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        email = data.get("address") or data.get("email")
        if not email:
            raise RuntimeError(f"Failed to parse email from server response: {data}")

        owner_token = data.get("owner_token", "")
        domain = data.get("domain", "")

        return Inbox(
            email=email,
            password=data.get("password", ""),
            provider="mocasus",
            meta={
                "owner_token": owner_token,
                "domain": domain,
                "expires_at": data.get("expires_at"),
                "tier": data.get("tier"),
            },
        )

    def wait_for_code(self, inbox: Inbox, timeout: int = 120, code_length: int = 6) -> str:
        """Poll for verification code using v2 messages endpoint."""
        return self._poll_loop(inbox, timeout, poll_interval=5.0, code_length=code_length)

    def get_messages(self, inbox: Inbox) -> list[dict]:
        """Get inbox messages via v2 API.

        GET ?action=messages&address=X&owner_token=Y
        Returns list of {id, from, subject, body, date, ...}
        """
        try:
            owner_token = inbox.meta.get("owner_token", "")
            r = self.session.get(
                self.BASE,
                params={
                    "action": "messages",
                    "address": inbox.email,
                    "owner_token": owner_token,
                },
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()

            # v2 may return {messages: [...]} or {data: [...]} or just [...]
            if isinstance(data, list):
                messages = data
            else:
                messages = data.get("messages") or data.get("data") or []

            # Normalize: ensure each msg has 'body' for _extract_otp
            for msg in messages:
                if "body" not in msg:
                    msg["body"] = (
                        msg.get("text")
                        or msg.get("html")
                        or msg.get("content")
                        or msg.get("subject", "")
                    )

            return messages
        except Exception:
            return []

    def delete_inbox(self, inbox: Inbox) -> bool:
        """Delete inbox via v2 API.

        POST ?action=delete + JSON body: {address, owner_token}
        """
        try:
            owner_token = inbox.meta.get("owner_token", "")
            r = self.session.post(
                self.BASE,
                params={"action": "delete"},
                json={
                    "address": inbox.email,
                    "owner_token": owner_token,
                },
                timeout=10,
            )
            if r.status_code < 300:
                resp = r.json()
                # Accept both {"ok": true} and {"ok": True} and {"status": "ok"}
                return resp.get("ok") is True or resp.get("ok") is not False or resp.get("status") == "ok"
            return False
        except Exception:
            return False
