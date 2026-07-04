# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in Morph Worker, please report it privately via:

- Email: andikastore.ads@gmail.com
- Telegram: @rubuskap

**Do not open a public issue.**

## Security Considerations

Morph Worker automates account creation on morphllm.com. Please:

1. **Do not abuse rate limits.** Use reasonable delays between accounts.
2. **Store API keys securely.** The `output/` directory contains plaintext credentials — treat it like a `.env` file.
3. **Use for testing only.** Bulk account generation is for development/testing purposes. Respect morphllm.com's Terms of Service.
4. **Keep API keys private.** Never commit the `output/` directory or `.env` files to version control.

## Credential Storage

- `output/state/` — Contains per-account credentials in JSON
- `~/.morph-worker/config.json` — Contains API keys for email providers

Both are excluded from git via `.gitignore`.
