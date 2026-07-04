# Morph Worker — Bulk Morph API Key Generator

**By mmoaa** | v0.1.0

---

## PRD (Product Requirements Document)

### 1. Problem Statement

Morph (morphllm.com) provides specialized AI models for coding agents (Fast Apply, WarpGrep, Compact, Router). Each account gets free API credits, but creating accounts manually is slow. Developers need bulk API keys for testing, benchmarking, and multi-agent setups.

### 2. Solution

**Morph Worker** — automated bulk account creation + API key extraction for morphllm.com. Supports multiple email providers (temp-mail + GSuite/Workspace) and outputs structured credentials ready for use.

### 3. Core Features

| Feature | Priority | Description |
|---------|----------|-------------|
| Email Provider Abstraction | P0 | Pluggable backends: Mocasus temp-mail API, GSuite/Google Workspace |
| Clerk Signup Automation | P0 | Browser automation for Clerk-hosted signup flow on morphllm.com |
| Email Verification | P0 | Auto-poll inbox for verification code, auto-submit |
| API Key Extraction | P0 | Navigate dashboard, generate/copy API key |
| Bulk Orchestrator | P0 | Run N accounts in parallel with configurable concurrency |
| CLI Interface | P1 | Node.js CLI (`morphworker`) with live progress |
| Credential Export | P1 | JSON / CSV / env format output |
| Resume Support | P2 | Skip already-created accounts, continue from where stopped |

### 4. Architecture

```
┌─────────────────────────────────────────────────┐
│                   CLI (Node.js)                   │
│              morphworker <command>                │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│              Orchestrator (Python)                │
│     ┌─────────────────────────────────────┐     │
│     │         Pipeline                     │     │
│     │  1. Email Gen → 2. Signup →         │     │
│     │  3. Verify → 4. API Key → 5. Save   │     │
│     └─────────────────────────────────────┘     │
└──────┬──────────────────────┬───────────────────┘
       │                      │
┌──────▼──────┐    ┌──────────▼──────────┐
│   Email      │    │   Browser            │
│   Providers  │    │   (Playwright)       │
│              │    │                      │
│ • Mocasus API│    │ • Clerk signup page  │
│ • GSuite     │    │ • Dashboard API keys │
└──────────────┘    └──────────────────────┘
```

### 5. Flow (per account)

```
1. Generate email → provider.create_inbox()
2. Navigate → morphllm.com → "Sign Up" (Clerk)
3. Fill form → email, password, name
4. Submit → Clerk sends verification code to inbox
5. Poll inbox → provider.wait_for_code(timeout=120s)
6. Submit code → account created
7. Navigate → morphllm.com/dashboard/api-keys
8. Click "Create API Key" → copy key
9. Save credentials → output/<email>.json
10. Repeat for next account
```

### 6. Email Provider Interface

```python
class EmailProvider:
    def create_inbox(self) -> Inbox        # Generate new email
    def wait_for_code(self, inbox, timeout) -> str  # Poll for verification code
    def delete_inbox(self, inbox) -> None  # Cleanup
```

**Implementations:**
- `MocasusProvider` — mocasus.my.id temp-mail API (key auth)
- `GSuiteProvider` — Google Workspace accounts (email aliasing / catch-all)

### 7. Tech Stack

- **CLI**: Node.js (consistent with Auto-FreeCF)
- **Core**: Python 3.11+ (Playwright, requests)
- **Browser**: Playwright (Chromium)
- **Storage**: JSON flat files (`output/`, `state/`)

### 8. Deliverables

- [x] `PRD.md` — This document
- [ ] `src/email_providers/base.py` — Abstract provider interface
- [ ] `src/email_providers/mocasus.py` — Mocasus temp-mail adapter
- [ ] `src/email_providers/gsuite.py` — GSuite adapter
- [ ] `src/browser/signup.py` — Clerk signup automation
- [ ] `src/browser/dashboard.py` — Dashboard + API key extraction
- [ ] `src/orchestrator.py` — Bulk pipeline orchestrator
- [ ] `src/config.py` — Config management
- [ ] `src/utils/export.py` — Credential export (JSON/CSV/env)
- [ ] `cli.js` — Node.js CLI wrapper
- [ ] `requirements.txt` — Python dependencies
- [ ] `package.json` — Node dependencies
- [ ] `assets/logo.svg` — Green Morph-style SVG logo
- [ ] `README.md` — Documentation

### 9. Anti-Detection Strategy

- Real browser fingerprint (Playwright non-headless mode optional)
- Human-like typing delays (100-300ms between keystrokes)
- Random viewport sizes
- Session persistence (cookies saved between runs)
- Rate limiting between accounts (3-5s delay + jitter)

### 10. Known Challenges

1. **Clerk bot detection** — Clerk has aggressive anti-bot. May need stealth plugins.
2. **IP rate limiting** — morphllm.com may rate-limit signups from same IP.
3. **Vercel firewall** — morphllm.com uses Vercel with security checkpoint.
4. **Captcha** — Clerk may present Turnstile/ReCAPTCHA on suspicious signups.
5. **API key only visible once** — Morph may show API key only at creation time.

### 11. Status: IN PROGRESS
