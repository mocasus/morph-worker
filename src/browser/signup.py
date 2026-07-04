"""Clerk Signup Automation via Playwright.
Handles the Clerk-hosted signup flow on morphllm.com.
"""
import asyncio
import random
import time
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser

class ClerkSignup:
    """Automate Clerk-based signup on morphllm.com."""

    MORPH_URL = "https://morphllm.com"
    SIGNUP_PATH = "/sign-up"  # Clerk-hosted

    def __init__(self, headless: bool = True, stealth: bool = True, output_dir: str = "output"):
        self.headless = headless
        self.stealth = stealth
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.browser: Browser = None
        self.context = None

    async def _launch(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )
        self.context = await self.browser.new_context(
            viewport={"width": random.randint(1280, 1440), "height": random.randint(800, 900)},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="Asia/Jakarta",
        )

        if self.stealth:
            await self._inject_stealth()

    async def _inject_stealth(self):
        """Inject anti-detection scripts."""
        page = await self.context.new_page()
        await page.add_init_script("""
            // Override navigator properties
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            // Override chrome runtime
            window.chrome = { runtime: {} };
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        """)
        await page.close()

    async def signup(self, email: str, password: str,
                     first_name: str = "Dev", last_name: str = "User") -> dict:
        """Execute full signup flow. Returns {success, email, password, session_cookies}."""
        if not self.browser:
            await self._launch()

        page = await self.context.new_page()
        result = {"success": False, "email": email, "password": password}

        try:
            # Step 1: Navigate to morphllm.com → click Sign Up
            await page.goto(self.MORPH_URL, wait_until="networkidle", timeout=30000)
            await self._human_delay(1, 2)

            # Find and click sign-up button
            signup_selectors = [
                'a[href*="sign-up"]', 'a[href*="signup"]', 'a[href*="register"]',
                'button:has-text("Sign Up")', 'button:has-text("Get Started")',
                'a:has-text("Sign Up")', 'a:has-text("Get started")',
            ]
            clicked = False
            for sel in signup_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                # Try direct Clerk signup URL
                await page.goto(f"{self.MORPH_URL}/sign-up", wait_until="networkidle", timeout=30000)

            await self._human_delay(2, 3)

            # Step 2: Fill Clerk signup form
            # Clerk uses specific component structure
            clerk_selectors = {
                "email": [
                    'input[name="email"]', 'input[type="email"]',
                    '#email', '.cl-formFieldInput[name="email"]',
                ],
                "password": [
                    'input[name="password"]', 'input[type="password"]',
                    '#password', '.cl-formFieldInput[name="password"]',
                ],
                "first_name": [
                    'input[name="firstName"]', 'input[name="first_name"]',
                    '#firstName', '#first_name',
                ],
                "last_name": [
                    'input[name="lastName"]', 'input[name="last_name"]',
                    '#lastName', '#last_name',
                ],
                "submit": [
                    'button[type="submit"]', 'button:has-text("Continue")',
                    'button:has-text("Sign Up")', 'button:has-text("Create account")',
                    '.cl-formButtonPrimary',
                ],
            }

            # Fill email
            for sel in clerk_selectors["email"]:
                try:
                    field = page.locator(sel).first
                    if await field.is_visible(timeout=3000):
                        await field.click()
                        await self._type_human(field, email)
                        break
                except Exception:
                    continue

            await self._human_delay(0.5, 1)

            # Click continue after email
            for sel in clerk_selectors["submit"]:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        break
                except Exception:
                    continue

            await self._human_delay(1, 2)

            # Fill password
            for sel in clerk_selectors["password"]:
                try:
                    field = page.locator(sel).first
                    if await field.is_visible(timeout=3000):
                        await field.click()
                        await self._type_human(field, password)
                        break
                except Exception:
                    continue

            await self._human_delay(0.5, 1)

            # Submit password
            for sel in clerk_selectors["submit"]:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        break
                except Exception:
                    continue

            await self._human_delay(3, 5)

            # Step 3: Check for verification code input
            verification_selectors = [
                'input[data-index="0"]', '.cl-otp-input',
                'input[name="code"]', 'input[aria-label*="code" i]',
                'input[aria-label*="verification" i]',
                'input[placeholder*="code" i]',
            ]

            needs_verification = False
            for sel in verification_selectors:
                try:
                    if await page.locator(sel).first.is_visible(timeout=2000):
                        needs_verification = True
                        break
                except Exception:
                    continue

            if needs_verification:
                # Verification needed — return to orchestrator for OTP extraction
                result["needs_verification"] = True
                result["state"] = "awaiting_code"
            else:
                # Check if we're on dashboard (signup succeeded without verification)
                dashboard_indicators = [
                    'text="API Keys"', 'text="Dashboard"',
                    'a[href*="api-keys"]', 'text="Create API Key"',
                ]
                on_dashboard = False
                for sel in dashboard_indicators:
                    try:
                        if await page.locator(sel).first.is_visible(timeout=2000):
                            on_dashboard = True
                            break
                    except Exception:
                        continue

                if on_dashboard:
                    result["success"] = True
                    result["state"] = "completed"
                else:
                    result["state"] = "unknown"

            # Save session cookies
            cookies = await self.context.cookies()
            result["cookies"] = cookies

            # Save state for resume
            state_file = self.output_dir / f"{email.replace('@','_')}_state.json"
            import json
            state_file.write_text(json.dumps({
                "email": email, "password": password,
                "state": result.get("state"), "cookies": cookies,
            }))

        except Exception as e:
            result["error"] = str(e)
        finally:
            await page.close()

        return result

    async def submit_verification_code(self, email: str, code: str) -> dict:
        """Submit verification code to Clerk."""
        # Reuse existing context if available
        page = await self.context.new_page()
        result = {"success": False}

        try:
            # Navigate to the page (should still be on verification)
            await page.goto(self.MORPH_URL, wait_until="networkidle", timeout=15000)
            await self._human_delay(1, 2)

            # Type each digit into OTP inputs
            otp_inputs = page.locator('.cl-otp-input, input[data-index]')
            count = await otp_inputs.count()

            if count > 0:
                for i, digit in enumerate(code):
                    if i < count:
                        await otp_inputs.nth(i).fill(digit)
                        await asyncio.sleep(0.1)
            else:
                # Single input field
                for sel in ['input[name="code"]', 'input[aria-label*="code" i]']:
                    try:
                        field = page.locator(sel).first
                        if await field.is_visible(timeout=2000):
                            await field.fill(code)
                            break
                    except Exception:
                        continue

            # Submit
            await self._human_delay(0.3, 0.8)
            for sel in ['button[type="submit"]', 'button:has-text("Verify")',
                        '.cl-formButtonPrimary', 'button:has-text("Continue")']:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        break
                except Exception:
                    continue

            await self._human_delay(3, 5)
            result["success"] = True
            result["cookies"] = await self.context.cookies()

        except Exception as e:
            result["error"] = str(e)
        finally:
            await page.close()

        return result

    async def extract_api_key(self) -> dict:
        """Navigate to dashboard and extract/create API key."""
        page = await self.context.new_page()
        result = {"success": False}

        try:
            # Navigate to API keys page
            await page.goto(f"{self.MORPH_URL}/dashboard/api-keys", wait_until="networkidle", timeout=30000)
            await self._human_delay(2, 3)

            # Check if we need to create a new key
            create_btn_selectors = [
                'button:has-text("Create")', 'button:has-text("New API Key")',
                'button:has-text("Generate")', 'a:has-text("Create API Key")',
                '.cl-formButtonPrimary:has-text("Create")',
            ]

            for sel in create_btn_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        await self._human_delay(1, 2)
                        break
                except Exception:
                    continue

            # Try to extract displayed API key
            key_selectors = [
                '[data-testid="api-key"]', '.api-key-value', 'code:has-text("morph_")',
                'pre:has-text("morph_")', 'input[value*="morph_"]',
                'text=/morph_[a-zA-Z0-9]+/',
            ]

            api_key = None
            for sel in key_selectors:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=3000):
                        text = await el.text_content() or await el.input_value()
                        import re
                        match = re.search(r'morph_[a-zA-Z0-9]+', text)
                        if match:
                            api_key = match.group(0)
                            break
                except Exception:
                    continue

            # Fallback: grab all page text and regex
            if not api_key:
                body = await page.content()
                import re
                match = re.search(r'morph_[a-zA-Z0-9]{20,}', body)
                if match:
                    api_key = match.group(0)

            if api_key:
                result["success"] = True
                result["api_key"] = api_key
            else:
                result["error"] = "API key not found on page"

        except Exception as e:
            result["error"] = str(e)
        finally:
            await page.close()

        return result

    async def close(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def _type_human(self, element, text: str):
        """Type with human-like delays."""
        for char in text:
            await element.type(char, delay=random.randint(50, 200))

    async def _human_delay(self, min_s: float, max_s: float):
        await asyncio.sleep(random.uniform(min_s, max_s))
