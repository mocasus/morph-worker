# 🦊 Morph Worker

<p align="center">
  <img src="assets/logo.svg" alt="Morph Worker" width="280" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-10B981?style=flat-square" alt="Version">
  <a href="https://www.npmjs.com/package/morph-worker"><img src="https://img.shields.io/npm/v/morph-worker?color=10B981&style=flat-square" alt="npm"></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/node-18+-green?style=flat-square" alt="Node">
  <img src="https://img.shields.io/badge/license-MIT-10B981?style=flat-square" alt="License">
</p>

<p align="center">
  <strong>Bulk API Key Generator for morphllm.com</strong><br>
  Automate account creation + API key extraction with temp-mail & GSuite support
</p>

---

## 🎯 What is Morph Worker?

**Morph Worker** automates the creation of [morphllm.com](https://morphllm.com) accounts and extracts their API keys — in bulk. Perfect for developers who need multiple API keys for testing, benchmarking, or multi-agent setups.

### Features

- ✅ **Bulk Account Creation** — Create N accounts with one command
- 📧 **Multiple Email Providers** — Mocasus temp-mail API + GSuite/Workspace
- 🤖 **Full Automation** — Clerk signup → email verification → API key extraction
- 🔄 **Resume Support** — Skip already-created accounts, continue from where stopped
- 📤 **Multi-format Export** — JSON / CSV / .env output
- 🎨 **Human-like** — Realistic typing delays, random viewports, stealth mode
- 🖥️ **CLI First** — Node.js CLI (`morphworker`) with live progress

---

## 📦 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Chromium** (for Playwright browser automation)

### Installation

```bash
# Install from npm
npm install -g morph-worker

# Install Python + Playwright deps
morphworker install
# Or manually:
# pip install -r requirements.txt && playwright install chromium
```

### Configuration

```bash
# Set up temp-mail API key
morphworker config --set mocasus_api_key=YOUR_KEY_HERE

# Show current config
morphworker config
```

### Usage

```bash
# Create 10 accounts
morphworker run 10

# Create 5 with concurrency
morphworker run 5 --concurrency 2

# Resume from where you stopped
morphworker run 10 --resume

# Show browser window (debug)
morphworker run 3 --no-headless

# Use GSuite email provider
morphworker run 5 --provider gsuite --password MyStrongPass123

# Export results
morphworker export --format csv
morphworker export --format env
```

### Using Python directly

```bash
python3 src/cli.py run 5
python3 src/cli.py config
python3 src/cli.py export --format json
```

---

## 🏗️ Architecture

```
morphworker <command>
       │
       ▼
┌──────────────┐    ┌───────────────────┐
│  CLI (Node)  │───▶│  Orchestrator (Py) │
└──────────────┘    └──────┬────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            │            ▼
    ┌─────────────┐        │   ┌──────────────┐
    │ Email Gen   │        │   │ Browser Auto │
    │ • mocasus   │        │   │ • Clerk Sign │
    │ • gsuite    │        │   │ • API Key    │
    └─────────────┘        │   └──────────────┘
                           ▼
                   ┌──────────────┐
                   │ Export       │
                   │ • JSON/CSV   │
                   │ • .env       │
                   └──────────────┘
```

### Pipeline (per account)

```
1. Generate Email → provider.create_inbox()
2. Clerk Signup   → morphllm.com → Fill form
3. Verify Email   → Poll inbox → Submit OTP
4. Extract Key    → Dashboard → Copy API key
5. Save           → output/state/account_N.json
```

---

## 📁 Project Structure

```
morph-worker/
├── assets/
│   └── logo.svg              # Green Morph-style logo
├── src/
│   ├── __init__.py
│   ├── cli.py                # Python CLI entry point
│   ├── config.py             # Configuration management
│   ├── orchestrator.py       # Bulk pipeline orchestrator
│   ├── email_providers/
│   │   ├── base.py           # Abstract provider interface
│   │   ├── mocasus.py        # Mocasus temp-mail adapter
│   │   └── gsuite.py         # GSuite adapter
│   ├── browser/
│   │   └── signup.py         # Playwright Clerk + Dashboard automation
│   └── utils/
│       └── export.py         # JSON/CSV/env export
├── output/                   # Generated credentials (gitignored)
│   └── state/                # Per-account state files
├── logs/                     # Runtime logs
├── cli.js                    # Node.js CLI wrapper
├── package.json
├── requirements.txt
├── PRD.md                    # Product Requirements Document
├── README.md
├── SECURITY.md
└── .gitignore
```

---

## 🔧 Configuration Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `email_provider` | string | `mocasus` | Email backend: `mocasus` \| `gsuite` |
| `mocasus_api_key` | string | — | API key for mocasus.my.id temp-mail |
| `gsuite_domain` | string | — | Google Workspace domain |
| `gsuite_admin_email` | string | — | Workspace admin for API ops |
| `headless` | bool | `true` | Run browser in headless mode |
| `stealth` | bool | `true` | Inject anti-detection scripts |
| `concurrency` | int | `1` | Parallel accounts |
| `default_password` | string | `MorphWorker2024!` | Default password for accounts |
| `export_format` | string | `json` | Export format: `json` \| `csv` \| `env` |

---

## ⚙️ Environment Variables

All config keys can also be set via environment variables:

```bash
export MOCASUS_API_KEY=your_key
export MORPH_EMAIL_PROVIDER=mocasus
export MORPH_CONCURRENCY=2
export MORPH_HEADLESS=false
```

---

## 🛡️ Security

Credentials are stored in `output/state/` — treat this directory like you would `.env` files:

- ✅ `output/` is gitignored
- ✅ API keys in `~/.morph-worker/config.json` are local
- ⚠️ Never commit credentials

See [SECURITY.md](SECURITY.md) for full policy.

---

## 📝 License

MIT — [mmoaa](https://github.com/mocasus)

---

<p align="center">
  <sub>Built with 🦊 by mmoaa</sub>
</p>
