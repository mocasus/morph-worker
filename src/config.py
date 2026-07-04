"""Configuration management for Morph Worker."""
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

CONFIG_DIR = Path.home() / ".morph-worker"
CONFIG_FILE = CONFIG_DIR / "config.json"

@dataclass
class Config:
    # Email provider
    email_provider: str = "mocasus"  # "mocasus" | "gsuite"
    mocasus_api_key: str = ""

    # GSuite
    gsuite_domain: str = ""
    gsuite_admin_email: str = ""

    # Browser
    headless: bool = True
    stealth: bool = True
    concurrency: int = 1

    # Output
    output_dir: str = "output"
    export_format: str = "json"  # json | csv | env

    # Account defaults
    default_password: str = "MorphWorker2024!"
    first_name: str = "Dev"
    last_name: str = "User"

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text())
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {k: getattr(self, k) for k in self.__dataclass_fields__}
        CONFIG_FILE.write_text(json.dumps(data, indent=2))

    @classmethod
    def from_env(cls) -> "Config":
        """Load from environment variables."""
        cfg = cls()
        env_map = {
            "MORPH_EMAIL_PROVIDER": "email_provider",
            "MOCASUS_API_KEY": "mocasus_api_key",
            "GSUITE_DOMAIN": "gsuite_domain",
            "MORPH_CONCURRENCY": "concurrency",
            "MORPH_HEADLESS": "headless",
            "MORPH_DEFAULT_PASSWORD": "default_password",
        }
        for env_key, field in env_map.items():
            val = os.environ.get(env_key)
            if val is not None:
                if field in ("concurrency",):
                    val = int(val)
                elif field in ("headless", "stealth"):
                    val = val.lower() in ("1", "true", "yes")
                setattr(cfg, field, val)
        return cfg
