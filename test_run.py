#!/usr/bin/env python3
"""Quick test: create 1 Morph account end-to-end."""
import asyncio, sys
sys.path.insert(0, '/root/morph-worker')

# Force the parent package so relative imports work
import src

from src.orchestrator import main_async

asyncio.run(main_async(count=1))
