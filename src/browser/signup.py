"""Clerk Signup Automation via Playwright.
Handles the Clerk-hosted signup flow on morphllm.com with full anti-detection.
"""
import asyncio
import random
import re
import json
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright_stealth import Stealth


# ── realistic user agents (Windows & macOS) ──────────────────────────
USER_AGENTS = [
    # Chrome 131 — Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Chrome 131 — macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Chrome 130 — Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Edge 131
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1920, "height": 1080},
]


class ClerkSignup:
    """Automate Clerk-based signup on morphllm.com with full stealth."""

    MORPH_URL = "https://morphllm.com"
    SIGNUP_PATH = "/sign-up"
    DASHBOARD_PATH = "/dashboard/api-keys"

    # ── email field selectors (Clerk uses name="emailAddress" for sign-up, "identifier" for sign-in) ──
    EMAIL_SELECTORS = [
        'input[name="emailAddress"]', '#emailAddress-field',
        'input[name="identifier"]', '#identifier-field',
        'input[name="email"]', 'input[type="email"]',
        '#email', '.cl-formFieldInput[name="email"]',
        '.cl-formFieldInput[name="identifier"]',
        '[data-auth-field="email"]', 'input[inputmode="email"]',
    ]
    PASSWORD_SELECTORS = [
        'input[name="password"]', '#password-field',
        'input[type="password"]', '#password',
        '.cl-formFieldInput[name="password"]',
        '[data-auth-field="password"]',
    ]

    def __init__(self, headless: bool = True, stealth: bool = True,
                 output_dir: str = "output"):
        self.headless = headless
        self.stealth = stealth
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self._pages: list[Page] = []

    # ── lifecycle ────────────────────────────────────────────────────

    async def ensure_launched(self):
        """Lazy-launch browser if not already running."""
        if self.browser and self.browser.is_connected():
            return
        await self._launch()

    async def _launch(self):
        """Launch Chromium with anti-detection flags + playwright-stealth."""
        self.playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )

        # ── context with realistic fingerprint ───────────────────────
        viewport = random.choice(VIEWPORTS)
        user_agent = random.choice(USER_AGENTS)

        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale="en-US",
            timezone_id="Asia/Jakarta",
        )

        # ── apply stealth to context ─────────────────────────────────
        if self.stealth:
            await self._apply_stealth()

    async def _apply_stealth(self):
        """Apply playwright-stealth evasion — minimal, matching working debug_v3."""
        stealth = Stealth()
        page = await self.context.new_page()
        try:
            await stealth.apply_stealth_async(self.context)
            print("    [stealth] playwright-stealth applied")
        except Exception as e:
            print(f"    [stealth] playwright-stealth failed: {e}")

        # Minimal extra: kill webdriver flag
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        """)
        await page.close()

    async def new_page(self) -> Page:
        """Create a new page and track it."""
        await self.ensure_launched()
        page = await self.context.new_page()
        self._pages.append(page)
        return page

    # ── signup flow ──────────────────────────────────────────────────

    async def signup(self, email: str, password: str,
                     first_name: str = "Dev", last_name: str = "User",
                     max_retries: int = 2) -> dict:
        """Execute full signup flow. Returns {success, email, password, ...}.

        Args:
            max_retries: Retry count if Vercel checkpoint or network error.
        """
        result = {"success": False, "email": email, "password": password}

        for attempt in range(max_retries + 1):
            try:
                page = await self.new_page()
                try:
                    result = await self._do_signup(
                        page, email, password, first_name, last_name
                    )
                    if result.get("success") or result.get("needs_verification"):
                        return result
                    # Only retry if we hit a checkpoint / transient error
                    if result.get("state") == "vercel_blocked":
                        print(f"  [retry {attempt+1}/{max_retries+1}] Vercel checkpoint — restarting browser...")
                        await self._restart_browser()
                        continue
                    # All other states (form_error, unknown, etc.): don't retry
                    return result
                finally:
                    await page.close()
            except Exception as e:
                if attempt < max_retries:
                    print(f"  [retry {attempt+1}/{max_retries}] Error: {e}")
                    await asyncio.sleep(2)
                else:
                    result["error"] = str(e)

        return result

    async def _do_signup(self, page: Page, email: str, password: str,
                         first_name: str, last_name: str) -> dict:
        """Core signup logic on a single page."""
        result = {
            "success": False,
            "email": email,
            "password": password,
            "state": "init",
        }

        # ── Step 0: Pass Vercel challenge on homepage first ──────────
        # Vercel sets a bypass cookie after the JS challenge completes.
        # Approach: load homepage → wait for challenge to resolve → proceed.
        print(f"    [_do_signup] goto {self.MORPH_URL}...")
        await page.goto(self.MORPH_URL, wait_until="domcontentloaded", timeout=30000)
        print(f"    [_do_signup] loaded, title='{(await page.title())[:80]}'")

        # Wait for Vercel challenge to resolve (max 30s = 15×2s)
        blocked_titles = ["Attention Required", "Just a moment",
                          "Vercel Security Checkpoint", "Checking your browser"]
        for i in range(15):
            await asyncio.sleep(2)
            title = await page.title()
            print(f"    [vc-check t={(i+1)*2}s] title='{title[:80]}' url={page.url[:80]}")
            if not any(t in title for t in blocked_titles):
                print(f"    [vc-check] ✅ passed at t={(i+1)*2}s")
                break
        else:
            # All attempts exhausted
            result["state"] = "vercel_blocked"
            result["error"] = f"Vercel security checkpoint ('{title}') — needs stronger stealth or proxy"
            return result

        # Verify we're on morphllm.com (not stuck on some redirect)
        if "morphllm.com" not in page.url:
            result["error"] = f"Redirected to unexpected URL: {page.url[:80]}"
            result["state"] = "vercel_blocked"
            return result

        # Wait for page to fully render (Vercel JS challenge runs first)
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass  # sometimes pages keep loading analytics

        await self._human_delay(1, 2)

        # ── Step 1: Verify we're on Clerk sign-up page ────────────────
        # If homepage redirect, go to sign-up explicitly
        current_url = page.url
        if "/sign-up" not in current_url and "/signup" not in current_url:
            # Try clicking sign-up link
            clicked = await self._click_first(page, [
                'a[href*="sign-up"]', 'a[href*="signup"]',
                'button:has-text("Sign Up")', 'a:has-text("Sign Up")',
            ], timeout=3000)
            if not clicked:
                await page.goto(f"{self.MORPH_URL}{self.SIGNUP_PATH}",
                                wait_until="domcontentloaded", timeout=20000)
            await self._human_delay(1, 2)

        # ── Wait for Clerk signup form to fully render (CSR) ────────
        print(f"    [_do_signup] waiting for Clerk signup form...")
        clerk_ready = False
        for i in range(15):
            try:
                el = page.locator('input[name="emailAddress"]').first
                if await el.count() > 0 and await el.is_visible(timeout=2000):
                    clerk_ready = True
                    print(f"    [_do_signup] Clerk form ready at t={(i+1)*2}s")
                    break
            except Exception:
                pass
            await asyncio.sleep(2)
        
        if not clerk_ready:
            # Fallback: try other selectors
            for sel in self.EMAIL_SELECTORS:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0 and await el.is_visible(timeout=2000):
                        clerk_ready = True
                        print(f"    [_do_signup] Clerk form found via '{sel}'")
                        break
                except Exception:
                    continue
        
        if not clerk_ready:
            # Debug: screenshot + dump DOM
            ts = datetime.now().strftime("%H%M%S")
            await page.screenshot(path=f"{self.output_dir}/signup_noform_{ts}.png")
            print(f"    [_do_signup] Clerk form NOT found — saved screenshot")
            result["error"] = "Clerk signup form did not render (CSR timeout)"
            result["state"] = "form_error"
            return result

        # ── Step 2: Fill Clerk signup form (both fields visible at once) ──
        filled_email = await self._fill_field(page, email, self.EMAIL_SELECTORS)
        if not filled_email:
            result["error"] = "Could not find email input field"
            result["state"] = "form_error"
            return result

        await self._human_delay(0.5, 1.0)

        # Check if password field is visible (Clerk one-step mode)
        pw_visible = await self._has_any(page, self.PASSWORD_SELECTORS, timeout=3000)

        if pw_visible:
            # One-step: fill password now
            await self._fill_field(page, password, self.PASSWORD_SELECTORS, timeout=5000)
        else:
            # Two-step: press Enter on email to reveal password
            try:
                field = page.locator(self.EMAIL_SELECTORS[0]).first
                await field.press("Enter")
                print("    [_do_signup] Enter on email (two-step transition)")
            except Exception:
                pass
            await self._human_delay(2, 3)
            await self._fill_field(page, password, self.PASSWORD_SELECTORS, timeout=5000)

        await self._human_delay(0.5, 0.8)

        # ── Submit via button click (NOT Enter press — Clerk SPA doesn't handle Enter) ──
        print("    [_do_signup] clicking Continue...")
        clicked = await self._click_first(page, [
            'button.cl-formButtonPrimary:not([disabled])',
            'button[type="submit"]:not([disabled])',
            'button:has-text("Continue"):not([disabled])',
            '.cl-formButtonPrimary:not([disabled])',
        ], timeout=5000)

        if not clicked:
            # Fallback: try Enter on the form element or body
            try:
                await page.locator('form').first.press("Enter")
                print("    [_do_signup] Enter on form (fallback)")
            except Exception:
                pass

        await self._human_delay(4, 7)

        # ── Check if name fields appear (Clerk sometimes asks after password) ──
        name_visible = False
        for sel in ['input[name="firstName"]', '#firstName', '[data-auth-field="firstName"]']:
            try:
                if await page.locator(sel).first.is_visible(timeout=2000):
                    name_visible = True
                    break
            except Exception:
                continue

        if name_visible:
            await self._fill_field(page, first_name, [
                'input[name="firstName"]', '#firstName',
                '[data-auth-field="firstName"]',
            ])
            await self._human_delay(0.3, 0.7)
            await self._fill_field(page, last_name, [
                'input[name="lastName"]', '#lastName',
                '[data-auth-field="lastName"]',
            ])
            await self._human_delay(0.5, 1)
            await self._click_first(page, [
                'button[type="submit"]', 'button:has-text("Continue")',
                '.cl-formButtonPrimary',
            ], timeout=3000)
            await self._human_delay(3, 5)

        # ── Check if redirected to sign-in after signup ──────────────
        # Clerk creates account then may show sign-in or redirect dashboard
        # Detect sign-in by checking for actual sign-in INPUT fields (not just .cl-signIn-root)
        is_signin = False
        try:
            si_field = page.locator('input[name="identifier"]').first
            if await si_field.count() > 0 and await si_field.is_visible(timeout=3000):
                is_signin = True
                print("    Detected sign-in identifier field visible")
        except Exception:
            pass
        
        if not is_signin:
            # Additional check: sign-in headers
            is_signin = await self._has_any(page, [
                'text="Sign in to your account"', 'h1:has-text("Sign in")',
            ], timeout=2000)

        if is_signin:
            print("    Clerk shows sign-in after signup — auto-signing in...")
            
            # ── Wait for sign-in form to render (CSR) ──────────────────
            print("    [signin] waiting for sign-in form...")
            signin_ready = False
            for i in range(15):
                try:
                    # Check for sign-in specific input: "identifier"
                    el = page.locator('input[name="identifier"]').first
                    if await el.count() > 0 and await el.is_visible(timeout=2000):
                        signin_ready = True
                        print(f"    [signin] identifier field ready at t={(i+1)*2}s")
                        break
                except Exception:
                    pass
                # Also check for emailAddress (some Clerk versions use it for sign-in too)
                try:
                    el = page.locator('input[name="emailAddress"]').first
                    if await el.count() > 0 and await el.is_visible(timeout=2000):
                        signin_ready = True
                        print(f"    [signin] emailAddress field ready at t={(i+1)*2}s")
                        break
                except Exception:
                    pass
                await asyncio.sleep(2)
            
            if not signin_ready:
                print("    [signin] sign-in form did not render — trying anyway...")
            
            # Sign-in form uses "identifier", not "emailAddress"
            SIGNIN_EMAIL_SELECTORS = [
                'input[name="identifier"]', '#identifier-field',
                '.cl-formFieldInput__identifier',
            ] + self.EMAIL_SELECTORS
            
            SIGNIN_PW_SELECTORS = [
                'input[name="password"]', '#password-field',
                'input[type="password"]',
            ] + [s for s in self.PASSWORD_SELECTORS if s not in [
                'input[name="password"]', '#password-field', 'input[type="password"]']]
            
            # Step 1: Fill email + click Continue
            ok = await self._fill_field(page, email, SIGNIN_EMAIL_SELECTORS, timeout=5000)
            print(f"    [signin] email filled: {ok}")
            await self._human_delay(0.5, 0.8)
            
            # Click Continue (NOT Enter — same SPA issue as signup)
            print("    [signin] clicking Continue...")
            await self._click_first(page, [
                'button.cl-formButtonPrimary:not([disabled])',
                'button[type="submit"]:not([disabled])',
                'button:has-text("Continue"):not([disabled])',
                '.cl-formButtonPrimary:not([disabled])',
            ], timeout=5000)
            
            await self._human_delay(3, 5)
            
            # Step 2: Check for errors
            has_error = await self._has_any(page, [
                'text="Invalid"', '.cl-formFieldError',
                'text="incorrect"', 'text="not found"',
            ], timeout=2000)
            if has_error:
                # Try screenshot but don't fail
                try:
                    ts = datetime.now().strftime("%H%M%S")
                    await page.screenshot(path=f"{self.output_dir}/signin_err_{ts}.png")
                except Exception:
                    pass
                print("    [signin] ⚠️  ERROR after email step!")
            
            # Step 3: Fill password
            ok = await self._fill_field(page, password, SIGNIN_PW_SELECTORS, timeout=5000)
            print(f"    [signin] password filled: {ok}")
            await self._human_delay(0.5, 0.8)
            
            # Click Continue/Sign In (NOT Enter)
            print("    [signin] clicking Sign In...")
            await self._click_first(page, [
                'button.cl-formButtonPrimary:not([disabled])',
                'button[type="submit"]:not([disabled])',
                'button:has-text("Continue"):not([disabled])',
                'button:has-text("Sign In"):not([disabled])',
                '.cl-formButtonPrimary:not([disabled])',
            ], timeout=5000)
            
            # Wait for redirect after sign-in (Clerk → app dashboard)
            await self._human_delay(3, 5)
            print(f"    [signin] post-submit URL: {page.url[:80]}")
            
            try:
                await page.wait_for_url(lambda url: "dashboard" in url, timeout=15000)
                print(f"    [signin] ✅ Redirected to: {page.url[:80]}")
            except Exception:
                print(f"    [signin] ❌ No redirect — current: {page.url[:80]}")
                
                # Debug: screenshot
                ts = datetime.now().strftime("%H%M%S")
                await page.screenshot(path=f"{self.output_dir}/signin_noredirect_{ts}.png")
                
                # Check for Clerk errors
                err_text = await self._get_error_text(page)
                if err_text:
                    print(f"    [signin] Clerk error: {err_text[:120]}")
                
                # Try clicking through from homepage
                await page.goto(f"{self.MORPH_URL}/dashboard",
                                wait_until="domcontentloaded", timeout=20000)
                await self._human_delay(2, 4)
                print(f"    [signin] after fallback nav: {page.url[:80]}")

        # ── Step 3: Check for verification code input ────────────────
        verification_selectors = [
            'input[data-index="0"]', '.cl-otp-input',
            'input[name="code"]', 'input[aria-label*="code" i]',
            'input[aria-label*="verification" i]',
            'input[placeholder*="code" i]',
            '[data-auth-field="code"]',
        ]

        needs_verification = False
        for sel in verification_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible(timeout=2000):
                    needs_verification = True
                    break
            except Exception:
                continue

        if needs_verification:
            result["needs_verification"] = True
            result["state"] = "awaiting_code"
            result["cookies"] = await self.context.cookies()
            return result

        # ── Step 4: Check if we landed on dashboard ──────────────────
        await self._human_delay(2, 3)
        on_dashboard = await self._has_any(page, [
            'text="API Keys"', 'text="Dashboard"',
            'a[href*="api-keys"]', 'text="Create API Key"',
            'text="Welcome"',
        ], timeout=5000)

        if on_dashboard:
            result["success"] = True
            result["state"] = "completed"
        else:
            current_url = page.url
            if "dashboard" in current_url:
                result["success"] = True
                result["state"] = "completed"
            else:
                result["state"] = "unknown"
                result["error"] = f"Not on dashboard after signup: {current_url[:80]}"

        # Save cookies
        result["cookies"] = await self.context.cookies()

        # Save state file
        state_file = self.output_dir / f"{email.replace('@', '_')}_state.json"
        state_file.write_text(json.dumps({
            "email": email, "password": password,
            "state": result.get("state"), "cookies": result.get("cookies"),
        }))

        return result

    async def submit_verification_code(self, email: str, code: str) -> dict:
        """Submit verification code to Clerk."""
        page = await self.new_page()
        result = {"success": False}

        try:
            await page.goto(self.MORPH_URL, wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(1, 2)

            # ── OTP inputs (Clerk uses individual digit inputs) ──────
            otp_inputs = page.locator('.cl-otp-input, input[data-index]')
            count = await otp_inputs.count()

            if count > 0:
                for i, digit in enumerate(code):
                    if i < count:
                        await otp_inputs.nth(i).click()
                        await otp_inputs.nth(i).fill(digit)
                        await asyncio.sleep(0.05)  # faster for OTP (user would paste)
            else:
                # Single input fallback
                for sel in ['input[name="code"]', 'input[aria-label*="code" i]',
                            'input[data-auth-field="code"]']:
                    try:
                        field = page.locator(sel).first
                        if await field.is_visible(timeout=2000):
                            await field.fill(code)
                            break
                    except Exception:
                        continue

            await self._human_delay(0.3, 0.8)

            # Submit
            await self._click_first(page, [
                'button[type="submit"]', 'button:has-text("Verify")',
                '.cl-formButtonPrimary', 'button:has-text("Continue")',
                'button:has-text("Submit")',
            ], timeout=3000)

            await self._human_delay(3, 5)

            # Check result
            current_url = page.url
            is_error = await self._has_any(page, [
                'text="Invalid"', 'text="incorrect"', 'text="expired"',
                '.cl-formFieldError',
            ], timeout=2000)

            if is_error:
                error_text = await page.text_content('.cl-formFieldError') or "Invalid code"
                result["error"] = error_text.strip()
            else:
                result["success"] = True
                result["cookies"] = await self.context.cookies()

        except Exception as e:
            result["error"] = str(e)
        finally:
            await page.close()

        return result

    async def extract_api_key(self, email: str = None, password: str = None) -> dict:
        """Navigate to dashboard and extract/create API key.

        If redirected to sign-in, auto-login with provided credentials.
        """
        page = await self.new_page()
        result = {"success": False}

        try:
            await page.goto(f"{self.MORPH_URL}{self.DASHBOARD_PATH}",
                            wait_until="domcontentloaded", timeout=30000)
            await self._human_delay(2, 4)

            # ── Auto sign-in if redirected ─────────────────────────
            if email and password:
                is_signin = await self._has_any(page, [
                    '.cl-signIn-root', 'text="Sign in to your account"',
                    'h2:has-text("Sign in")',
                ], timeout=3000)

                if is_signin:
                    print("    API key page redirected to sign-in — auto-logging in...")
                    
                    # Use sign-in specific selectors (Clerk sign-in uses "identifier" not "emailAddress")
                    SIGNIN_EMAIL = [
                        'input[name="identifier"]', '#identifier-field',
                        '.cl-formFieldInput__identifier',
                    ] + self.EMAIL_SELECTORS
                    
                    await self._fill_field(page, email, SIGNIN_EMAIL, timeout=5000)
                    await self._human_delay(0.5, 1)
                    await self._click_first(page, [
                        'button.cl-formButtonPrimary:not([disabled])',
                        'button[type="submit"]:not([disabled])',
                        'button:has-text("Continue"):not([disabled])',
                        '.cl-formButtonPrimary:not([disabled])',
                    ], timeout=5000)
                    await self._human_delay(2, 3)
                    await self._fill_field(page, password, self.PASSWORD_SELECTORS, timeout=5000)
                    await self._human_delay(0.5, 1)
                    await self._click_first(page, [
                        'button.cl-formButtonPrimary:not([disabled])',
                        'button[type="submit"]:not([disabled])',
                        'button:has-text("Continue"):not([disabled])',
                        'button:has-text("Sign In"):not([disabled])',
                        '.cl-formButtonPrimary:not([disabled])',
                    ], timeout=5000)
                    await self._human_delay(3, 5)

                    # Re-navigate to dashboard after login
                    await page.goto(f"{self.MORPH_URL}{self.DASHBOARD_PATH}",
                                    wait_until="domcontentloaded", timeout=30000)
                    await self._human_delay(2, 4)

            # If no API keys page, try navigating from dashboard
            if "api-keys" not in page.url:
                # Try clicking through from dashboard
                await page.goto(f"{self.MORPH_URL}/dashboard",
                                wait_until="domcontentloaded", timeout=20000)
                await self._human_delay(1, 2)
                await self._click_first(page, [
                    'a[href*="api-keys"]', 'text="API Keys"',
                    'button:has-text("API Keys")',
                ], timeout=5000)
                await self._human_delay(2, 3)

            # Always try to create a new key first
            await self._click_first(page, [
                'button:has-text("Create")', 'button:has-text("New API Key")',
                'button:has-text("Generate")', 'a:has-text("Create API Key")',
                '.cl-formButtonPrimary:has-text("Create")',
                'button:has-text("Add")',
            ], timeout=4000)
            await self._human_delay(1, 3)

            # Extract displayed API key
            api_key = None
            body_text = await page.content()

            # Try explicit selectors first
            for sel in [
                '[data-testid="api-key"]', '.api-key-value',
                'code:has-text("morph_")', 'pre:has-text("morph_")',
                'input[value*="morph_"]', '[data-clipboard-text]',
                '.key-display', '[class*="key"]',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0 and await el.is_visible(timeout=2000):
                        text = await el.text_content() or await el.input_value() or ""
                        match = re.search(r'morph_[a-zA-Z0-9]+', text)
                        if match:
                            api_key = match.group(0)
                            break
                except Exception:
                    continue

            # Fallback: regex on full page content
            if not api_key:
                match = re.search(r'morph_[a-zA-Z0-9]{20,}', body_text)
                if match:
                    api_key = match.group(0)

            # Fallback: look for any text node containing "morph_"
            if not api_key:
                match = re.search(r'morph_\w+', body_text)
                if match:
                    api_key = match.group(0)

            if api_key:
                result["success"] = True
                result["api_key"] = api_key
            else:
                result["error"] = "API key not found on page — may need manual extraction"

        except Exception as e:
            result["error"] = str(e)
        finally:
            await page.close()

        return result

    # ── helpers ──────────────────────────────────────────────────────

    async def _restart_browser(self):
        """Close and restart browser context."""
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        self.browser = None
        self.context = None
        self._pages.clear()
        await asyncio.sleep(1)
        await self._launch()

    async def _click_first(self, page: Page, selectors: list[str],
                           timeout: int = 3000) -> bool:
        """Try each selector, click the first visible one."""
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible(timeout=timeout):
                    await el.click()
                    return True
            except Exception:
                continue
        return False

    async def _fill_field(self, page: Page, value: str,
                          selectors: list[str], timeout: int = 5000) -> bool:
        """Fill the first visible field from selectors."""
        for sel in selectors:
            try:
                field = page.locator(sel).first
                if await field.count() > 0 and await field.is_visible(timeout=timeout):
                    await field.click()
                    await self._type_human(field, value)
                    return True
            except Exception:
                continue
        return False

    async def _has_any(self, page: Page, selectors: list[str],
                       timeout: int = 3000) -> bool:
        """Check if any selector is visible."""
        for sel in selectors:
            try:
                if await page.locator(sel).first.is_visible(timeout=timeout):
                    return True
            except Exception:
                continue
        return False

    async def _type_human(self, element, text: str):
        """Type with human-like delays."""
        for char in text:
            await element.type(char, delay=random.randint(30, 150))

    async def _human_delay(self, min_s: float, max_s: float):
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _get_error_text(self, page: Page) -> str:
        """Extract visible Clerk error messages."""
        for sel in ['.cl-formFieldError', '.cl-errorText', '[data-error]',
                     '.alert-danger', '.text-error', '[class*="error"]']:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible(timeout=1000):
                    return (await el.text_content() or "").strip()
            except Exception:
                continue
        return ""

    # ── cleanup ──────────────────────────────────────────────────────

    async def close(self):
        """Close all resources."""
        for page in self._pages:
            try:
                await page.close()
            except Exception:
                pass
        self._pages.clear()
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
