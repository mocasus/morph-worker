"""GSuite / Google Workspace Email Provider.
Uses existing Workspace accounts — creates email aliases or uses catch-all.
"""
from .base import EmailProvider, Inbox

class GSuiteProvider(EmailProvider):
    """Google Workspace email — aliasing on existing domain."""

    name = "gsuite"

    def __init__(self, domain: str, admin_email: str = None):
        """
        Args:
            domain: Workspace domain (e.g., mycompany.com)
            admin_email: Optional admin for API operations
        """
        self.domain = domain
        self.admin_email = admin_email
        self._counter = 0

    def create_inbox(self, username: str = None) -> Inbox:
        """Create email alias. Falls back to '+' aliasing if no API access."""
        import uuid
        self._counter += 1
        local = username or f"morph{self._counter:03d}{uuid.uuid4().hex[:4]}"
        email = f"{local}@{self.domain}"
        return Inbox(email=email, password="", provider="gsuite", meta={"alias": local})

    def wait_for_code(self, inbox: Inbox, timeout: int = 120, code_length: int = 6) -> str:
        """GSuite doesn't support API polling — raise with instructions."""
        raise NotImplementedError(
            "GSuite Provider requires manual OTP entry. "
            "Use Gmail API polling (not yet implemented) or switch to temp-mail provider."
        )

    def get_messages(self, inbox: Inbox) -> list[dict]:
        """Not implemented for GSuite without Gmail API."""
        return []
