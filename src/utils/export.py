"""Credential export utilities."""
import json
import csv
import os
from pathlib import Path
from datetime import datetime

def export_json(accounts: list[dict], output_path: str) -> str:
    """Export accounts to JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated_at": datetime.now().isoformat(),
        "count": len(accounts),
        "service": "morphllm.com",
        "accounts": accounts,
    }
    path.write_text(json.dumps(data, indent=2))
    return str(path)

def export_csv(accounts: list[dict], output_path: str) -> str:
    """Export accounts to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["email", "password", "api_key", "created_at"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(accounts)
    return str(path)

def export_env(accounts: list[dict], output_path: str) -> str:
    """Export accounts as .env format (MORPH_API_KEY=...)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# Morph Worker — {len(accounts)} accounts",
             f"# Generated: {datetime.now().isoformat()}", ""]
    for i, acc in enumerate(accounts):
        key = acc.get("api_key", "")
        email = acc.get("email", "")
        lines.append(f"# Account {i+1}: {email}")
        lines.append(f'MORPH_API_KEY_{i+1}="{key}"')
        lines.append("")

    path.write_text("\n".join(lines))
    return str(path)

def export(accounts: list[dict], format: str = "json", output_dir: str = "output") -> str:
    """Export accounts in specified format. Returns output path."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = {"json": "json", "csv": "csv", "env": "env"}.get(format, "json")
    output_path = os.path.join(output_dir, f"morph_accounts_{ts}.{ext}")

    if format == "csv":
        return export_csv(accounts, output_path)
    elif format == "env":
        return export_env(accounts, output_path)
    else:
        return export_json(accounts, output_path)
