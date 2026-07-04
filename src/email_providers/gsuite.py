"""GSuite / Google Workspace Email Provider.
Uses existing Workspace accounts — creates email aliases or uses catch-all.

STATUS: PLACEHOLDER — full Gmail API integration not yet implemented.
Use MocasusProvider for automated verification.
"""
from .base import EmailProvider, Inbox


class GSuiteProvider(EmailProvider):
    """Google Workspace email — aliasing on existing domain.

    NOTE: This provider creates emails but CANNOT auto-verify them.
    The wait_for_code() method raises a clear error with instructions.
    For fully automated flows, use MocasusProvider.
    """

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
        """GSuite polling requires Gmail API — not yet implemented.

        Raises RuntimeError with clear user instructions.
        """
        raise RuntimeError(
            "\n"
            "╔══════════════════════════════════════════════════╗\n"
            "║  GSuite Provider — Manual Action Required         ║\n"
            "╠══════════════════════════════════════════════════╣\n"
            "║  Gmail API polling is not yet implemented.        ║\n"
            "║                                                    ║\n"
            "║  Options:                                          ║\n"
            "║  1. Use 'mocasus' provider for full automation    ║\n"
            "║  2. Set up Gmail API + wait for implementation    ║\n"
            "║  3. Use manual OTP entry (not yet supported)      ║\n"
            "║                                                    ║\n"
            "║  Switch provider:                                  ║\n"
            "║  morphworker config --set email_provider=mocasus  ║\n"
            "╚══════════════════════════════════════════════════╝\n"
        )

    def get_messages(self, inbox: Inbox) -> list[dict]:
        """Not implemented for GSuite without Gmail API."""
        return []
