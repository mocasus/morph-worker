"""Email Provider abstract interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import time

@dataclass
class Inbox:
    email: str
    password: str = ""
    provider: str = ""
    meta: dict = field(default_factory=dict)

class EmailProvider(ABC):
    """Abstract email provider for signup verification."""

    name: str = "base"

    @abstractmethod
    def create_inbox(self, username: Optional[str] = None) -> Inbox:
        """Generate a new disposable inbox. Returns Inbox with email + credentials."""

    @abstractmethod
    def wait_for_code(self, inbox: Inbox, timeout: int = 120, code_length: int = 6) -> str:
        """Poll inbox until verification code arrives or timeout.
        Returns the extracted code string."""

    @abstractmethod
    def get_messages(self, inbox: Inbox) -> list[dict]:
        """Get all messages in inbox. Returns list of {id, from, subject, body, date}."""

    def delete_inbox(self, inbox: Inbox) -> bool:
        """Cleanup. Default: no-op."""
        return True

    def _extract_otp(self, body: str, length: int = 6) -> Optional[str]:
        """Extract OTP code from email body."""
        import re
        # Common patterns: "code: 123456", "OTP: 123456", just "123456"
        patterns = [
            rf'(?:code|otp|verification|verify|kode|token)\s*(?::|is|adalah|=|->)?\s*(\d{{{length}}})',
            rf'(?<!\d)(\d{{{length}}})(?!\d)',
        ]
        for pat in patterns:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _poll_loop(self, inbox: Inbox, timeout: int, poll_interval: float = 3.0,
                   code_length: int = 6) -> str:
        """Standard polling loop: check messages every N seconds until code found or timeout."""
        deadline = time.time() + timeout
        last_count = 0
        while time.time() < deadline:
            msgs = self.get_messages(inbox)
            if len(msgs) > last_count:
                last_count = len(msgs)
                # Check newest messages first
                for msg in reversed(msgs):
                    body = msg.get("body", "") or msg.get("text", "") or msg.get("html", "")
                    if isinstance(body, list):
                        body = " ".join(body)
                    code = self._extract_otp(str(body), code_length)
                    if code:
                        return code
            time.sleep(poll_interval)
        raise TimeoutError(f"No verification code received within {timeout}s for {inbox.email}")
