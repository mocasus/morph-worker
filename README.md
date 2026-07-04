# 🦊 Morph Worker

<p align="center">
  <img src="assets/logo.svg" alt="Morph Worker" width="280" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.0--dev-10B981?style=flat-square" alt="Version">
  <a href="https://www.npmjs.com/package/morph-worker"><img src="https://img.shields.io/npm/v/morph-worker?color=10B981&style=flat-square" alt="npm"></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/node-18+-green?style=flat-square" alt="Node">
  <img src="https://img.shields.io/badge/license-MIT-10B981?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/status-alpha-red?style=flat-square" alt="Status">
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
- 🤖 **Full Automation** — Clerk signup → onboarding → API key extraction
- 🔄 **Resume Support** — Skip already-created accounts, continue from where stopped
- 📤 **Multi-format Export** — JSON / CSV / .env output
- 🎨 **Human-like** — Realistic typing delays, random viewports, stealth mode
- 🖥️ **CLI First** — Node.js CLI (`morphworker`) with live progress

---

## ⚠️ Current Status: Alpha

Morph Worker is under active development. The core signup flow works but faces two challenges:

| Issue | Status | Detail |
|-------|--------|--------|
| Clerk Rate Limiting | ⚠️ Mitigated | 429 on `clerk.morphllm.com` after multiple signups — auto-detected with backoff |
| Vercel Checkpoint | ❌ Blocked | Bot detection on `www.morphllm.com` — requires residential proxy or manual cookie injection |
| Onboarding Flow | 🔧 WIP | 6-step post-signup onboarding not yet automated (manual bypass required) |

**Current workaround:** Complete onboarding manually on mobile, then feed the `__session` cookie or API key to the worker.

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

# Skip API key extraction (complete onboarding on phone)
morphworker run 5 --skip-extract
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

### Full Pipeline (per account)

```
1. Generate Email  → provider.create_inbox()
2. Clerk Signup    → morphllm.com/sign-up → Fill form (email + password)
3. Email Verify    → Poll inbox → Extract OTP code → Submit
4. Sign In         → Clerk redirects to sign-in → Auto-login
5. Onboarding*     → /onboarding → /onboarding/2 → /onboarding/3 (team?)
                      → /onboarding/5 (use case?) → Welcome page
6. Extract Key     → /dashboard/api-keys → Copy/create API key
7. Save            → output/state/account_N.json
```

*\*Onboarding is a 5-6 step interactive flow with user choices. Currently requires manual completion or cookie injection.*

### Clerk Flow Deep-dive

```
morphllm.com/sign-up
    │
    ▼
Clerk SPA loads (clerk.morphllm.com)
    │
    ├─ Step 1: Fill email + password (one-step)
    │          OR Fill email → Continue → Fill password (two-step)
    │          → Click "Continue" button (NOT Enter — React SPA quirk)
    │
    ├─ Step 2: Optional — name fields (firstName/lastName)
    │
    ├─ Step 3: OTP verification code (from email)
    │          → Fill 6-digit code into Clerk OTP inputs
    │
    ▼
Clerk auto-redirects to sign-in
    │
    ├─ Fill "identifier" field (email)
    │  → Click "Continue"
    │  → Fill password
    │  → Click "Continue" / "Sign In"
    │
    ▼
morphllm.com/onboarding    (manual for now)
morphllm.com/onboarding/2
morphllm.com/onboarding/3
morphllm.com/onboarding/5
morphllm.com/onboarding/?u=...  (Welcome + curl)
    │
    ▼
morphllm.com/dashboard/api-keys  ← API key here
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
│   │   └── gsuite.py         # GSuite adapter (placeholder — needs OAuth)
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

## 🐛 Known Issues

1. **Vercel Checkpoint** — `www.morphllm.com` triggers Vercel bot detection on headless browsers. Workaround: inject authenticated `__session` cookie or use residential proxy.
2. **Clerk 429** — Clerk CDN rate-limits after ~5 signup attempts per IP. Mitigation: auto-detect and abort with backoff timer.
3. **Onboarding Not Automated** — The 5-step Morph onboarding flow after sign-in requires manual interaction. Will be automated in future release.
4. **GSuite Provider** — Placeholder only. Needs OAuth2 service account setup with Google Workspace Admin SDK.
5. **Enter Key** — Clerk SPA (React) does not handle Enter for form submission. Always use explicit button clicks.

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
  <img src="https://img.shields.io/badge/version-0.2.0--dev-10B981?style=flat-square" alt="Version">
</p>
<p align="center">
  <sub>Built with 🦊 by mmoaa</sub>
</p>
