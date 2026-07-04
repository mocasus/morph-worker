"""Morph Worker — Bulk Morph API Key Generator.
CLI entry point.
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Morph Worker — Bulk Morph API Key Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  morphworker run 10                    # Create 10 accounts
  morphworker run 5 --resume           # Resume from state
  morphworker config                   # Show current config
  morphworker config --set api-key=KEY # Set config value
  morphworker export --format csv      # Export results as CSV
        """
    )

    sub = parser.add_subparsers(dest="command")

    # run
    run_parser = sub.add_parser("run", help="Run bulk account creation")
    run_parser.add_argument("count", type=int, help="Number of accounts")
    run_parser.add_argument("--resume", action="store_true", help="Skip already-created")
    run_parser.add_argument("--no-headless", action="store_true", help="Show browser")
    run_parser.add_argument("--concurrency", type=int, default=1)
    run_parser.add_argument("--provider", choices=["mocasus", "gsuite"])
    run_parser.add_argument("--password", type=str)
    run_parser.add_argument("--output", type=str)

    # config
    config_parser = sub.add_parser("config", help="Manage config")
    config_parser.add_argument("--set", type=str, help="Set key=value pairs (comma separated)")
    config_parser.add_argument("--reset", action="store_true")

    # export
    export_parser = sub.add_parser("export", help="Export results")
    export_parser.add_argument("--format", choices=["json", "csv", "env"], default="json")
    export_parser.add_argument("--output", type=str)

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(_run(args))
    elif args.command == "config":
        _config_cmd(args)
    elif args.command == "export":
        _export_cmd(args)
    else:
        parser.print_help()


async def _run(args):
    cfg = Config.load()

    if args.provider:
        cfg.email_provider = args.provider
    if args.password:
        cfg.default_password = args.password
    if args.concurrency:
        cfg.concurrency = args.concurrency
    if args.no_headless:
        cfg.headless = False
    if args.output:
        cfg.output_dir = args.output

    print(f"🚀 Morph Worker — Creating {args.count} accounts")
    print(f"   Provider: {cfg.email_provider}")
    print(f"   Concurrency: {cfg.concurrency}")
    print(f"   Headless: {cfg.headless}")
    print()

    orch = Orchestrator(cfg)
    await orch.run(count=args.count, resume=args.resume)

    if orch.results:
        orch.save_results()
    print(orch.summary())


def _config_cmd(args):
    cfg = Config.load()

    if args.reset:
        cfg = Config()
        cfg.save()
        print("✅ Config reset to defaults")
        return

    if args.set:
        for pair in args.set.split(","):
            k, v = pair.split("=", 1)
            k = k.strip().lower().replace("-", "_")
            v = v.strip()
            if hasattr(cfg, k):
                # Type coercion
                current = getattr(cfg, k)
                if isinstance(current, bool):
                    v = v.lower() in ("1", "true", "yes")
                elif isinstance(current, int):
                    v = int(v)
                setattr(cfg, k, v)
                print(f"✅ {k} = {v}")
            else:
                print(f"⚠️ Unknown config key: {k}")
        cfg.save()
        return

    # Show config
    print("Morph Worker Config")
    print("=" * 40)
    for field in cfg.__dataclass_fields__:
        val = getattr(cfg, field)
        if field == "mocasus_api_key" and val:
            val = val[:8] + "..." if len(val) > 8 else val
        print(f"  {field}: {val}")


def _export_cmd(args):
    import json
    from src.utils.export import export

    output_dir = args.output or "output"
    results = []
    state_dir = Path(output_dir) / "state"
    if state_dir.exists():
        for f in sorted(state_dir.glob("account_*.json")):
            results.append(json.loads(f.read_text()))

    if not results:
        print("No results found in output/state/")
        return

    path = export(results, format=args.format, output_dir=output_dir)
    print(f"✅ Exported {len(results)} accounts → {path}")


if __name__ == "__main__":
    main()
