#!/usr/bin/env python3
"""Debug: screenshot morphllm.com signup page to see current Clerk structure."""
import asyncio, sys
sys.path.insert(0, '/root/morph-worker')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    ctx = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    )
    
    # Apply stealth
    stealth = Stealth()
    page = await ctx.new_page()
    await stealth.apply_stealth_async(ctx)
    await page.close()
    
    page = await ctx.new_page()
    await page.goto("https://morphllm.com", wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)
    
    # Check title
    title = await page.title()
    print(f"Page title: {title}")
    print(f"URL: {page.url}")
    
    # Screenshot
    await page.screenshot(path="/tmp/morph_debug.png", full_page=False)
    print("Screenshot saved to /tmp/morph_debug.png")
    
    # Try clicking sign up
    for sel in ['a[href*="sign-up"]', 'a[href*="signup"]', 'button:has-text("Sign Up")', 'a:has-text("Sign Up")', 'text="Sign Up"']:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                print(f"Found: {sel} (visible: {await el.is_visible()})")
        except:
            pass
    
    # Wait and go to signup page directly
    await page.goto("https://morphllm.com/sign-up", wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)
    
    # Screenshot signup
    await page.screenshot(path="/tmp/morph_signup_debug.png", full_page=False)
    print("Signup screenshot saved to /tmp/morph_signup_debug.png")
    
    # Dump page HTML (truncated)
    html = await page.content()
    # Look for email-related elements
    import re
    for pattern in ['input.*email', 'input.*type.*email', 'sign-up', 'signup', 'Clerk', 'clerk']:
        matches = re.findall(pattern, html, re.IGNORECASE)
        print(f"Pattern '{pattern}': {len(matches)} matches - {matches[:3]}")
    
    await browser.close()
    await pw.stop()

asyncio.run(main())
