"""Bulk orchestrator — pipeline manager for mass account creation."""
import asyncio
import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from .email_providers.base import EmailProvider, Inbox
from .email_providers.mocasus import MocasusProvider
from .email_providers.gsuite import GSuiteProvider
from .browser.signup import ClerkSignup
from .config import Config
from .utils.export import export


class Orchestrator:
    """Manages bulk account creation pipeline."""

    def __init__(self, config: Config):
        self.config = config
        self.email_provider = self._init_email_provider()
        self.output_dir = Path(config.output_dir or "output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir = self.output_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[dict] = []
        self._semaphore = asyncio.Semaphore(max(1, config.concurrency))

    def _init_email_provider(self) -> EmailProvider:
        if self.config.email_provider == "gsuite":
            return GSuiteProvider(
                domain=self.config.gsuite_domain,
                admin_email=self.config.gsuite_admin_email,
            )
        else:
            if not self.config.mocasus_api_key:
                raise ValueError("MOCASUS_API_KEY is required. Set in config or MORPH_MOCASUS_API_KEY env.")
            return MocasusProvider(api_key=self.config.mocasus_api_key)

    async def run(self, count: int, resume: bool = False) -> list[dict]:
        """Run bulk account creation pipeline.

        Args:
            count: Number of accounts to create
            resume: Skip accounts already in state/

        Returns:
            List of account dicts: {email, password, api_key, created_at, error?}
        """
        already_done = set()
        if resume:
            already_done = self._load_existing()

        accounts = []
        tasks = []
        for i in range(count):
            if i in already_done:
                continue
            tasks.append(self._process_account(i))

        # Run with concurrency control
        sem = asyncio.Semaphore(self.config.concurrency)

        async def bounded(task_idx):
            async with sem:
                return await self._process_account(task_idx)

        results = await asyncio.gather(*[bounded(i) for i in range(count) if i not in already_done],
                                       return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                accounts.append({"error": str(r), "created_at": datetime.now().isoformat()})
            else:
                accounts.append(r)

        # Merge with already-done accounts
        for i in sorted(already_done):
            state_file = self.state_dir / f"account_{i:04d}.json"
            if state_file.exists():
                accounts.insert(i, json.loads(state_file.read_text()))

        self.results = accounts
        return accounts

    async def _process_account(self, index: int) -> dict:
        """Full pipeline for one account."""
        result = {
            "index": index,
            "email": "",
            "password": self.config.default_password,
            "api_key": None,
            "created_at": datetime.now().isoformat(),
            "success": False,
        }

        signup = ClerkSignup(
            headless=self.config.headless,
            stealth=self.config.stealth,
            output_dir=str(self.output_dir),
        )

        try:
            # Step 1: Generate email
            print(f"[{index}] Creating inbox...")
            inbox = self.email_provider.create_inbox()
            result["email"] = inbox.email
            result["inbox_meta"] = inbox.meta
            print(f"[{index}] Inbox: {inbox.email}")

            # Step 2: Signup via Clerk
            print(f"[{index}] Starting signup...")
            signup_result = await signup.signup(
                email=inbox.email,
                password=result["password"],
                first_name=self.config.first_name,
                last_name=self.config.last_name,
            )

            if signup_result.get("needs_verification"):
                # Step 3: Wait for verification code
                print(f"[{index}] Waiting for verification code...")
                try:
                    code = self.email_provider.wait_for_code(inbox, timeout=120)
                    print(f"[{index}] Got code: {code}")

                    # Submit code
                    verify_result = await signup.submit_verification_code(inbox.email, code)
                    if not verify_result.get("success"):
                        result["error"] = f"Verification failed: {verify_result.get('error')}"
                        return result
                except TimeoutError:
                    result["error"] = "Verification code timeout"
                    return result
            elif not signup_result.get("success") and signup_result.get("state") != "completed":
                result["error"] = f"Signup failed: {signup_result.get('error', 'unknown')}"
                return result

            print(f"[{index}] Signup complete, extracting API key...")

            # Step 4: Extract API key
            key_result = await signup.extract_api_key()
            if key_result.get("success"):
                result["api_key"] = key_result["api_key"]
                result["success"] = True
                print(f"[{index}] API key: {result['api_key'][:20]}...")
            else:
                result["error"] = f"API key extraction failed: {key_result.get('error')}"
                result["api_key"] = "MANUAL_EXTRACTION_NEEDED"

            # Save state
            state_file = self.state_dir / f"account_{index:04d}.json"
            state_file.write_text(json.dumps(result, indent=2))

        except Exception as e:
            result["error"] = str(e)
        finally:
            await signup.close()

        return result

    def _load_existing(self) -> set[int]:
        """Find already-processed accounts."""
        existing = set()
        if self.state_dir.exists():
            for f in sorted(self.state_dir.glob("account_*.json")):
                try:
                    idx = int(f.stem.split("_")[1])
                    existing.add(idx)
                except (ValueError, IndexError):
                    continue
        return existing

    def save_results(self):
        """Export all results to file."""
        fmt = self.config.export_format or "json"
        output_path = export(self.results, format=fmt, output_dir=str(self.output_dir))
        print(f"\n✅ Exported {len(self.results)} accounts → {output_path}")
        return output_path

    def summary(self) -> str:
        """Generate summary of run."""
        success = sum(1 for r in self.results if r.get("success"))
        failed = sum(1 for r in self.results if r.get("error") and not r.get("success"))
        manual = sum(1 for r in self.results if r.get("api_key") == "MANUAL_EXTRACTION_NEEDED")

        lines = [
            f"\n{'='*50}",
            f" Morph Worker — Run Summary",
            f" Time: {datetime.now().isoformat()}",
            f"{'='*50}",
            f" Total:  {len(self.results)}",
            f" ✅ OK:   {success}",
            f" ❌ Fail: {failed}",
            f" ⚠️ Manual:{manual}",
            f"{'='*50}",
        ]

        for r in self.results:
            status = "✅" if r.get("success") else "❌" if r.get("error") else "⚠️"
            key_info = ""
            if r.get("api_key"):
                k = r["api_key"]
                key_info = f" → {k[:16]}..." if k != "MANUAL_EXTRACTION_NEEDED" else " → manual"
            lines.append(f" {status} {r.get('email', '?')}{key_info}")
            if r.get("error"):
                lines.append(f"    ↳ {r['error'][:80]}")

        return "\n".join(lines)


async def main_async(count: int, config: Config = None, resume: bool = False):
    """Entry point for async CLI use."""
    if config is None:
        config = Config.load()

    orch = Orchestrator(config)
    await orch.run(count=count, resume=resume)

    if orch.results:
        orch.save_results()
    print(orch.summary())
