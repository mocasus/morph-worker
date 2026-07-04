#!/usr/bin/env python3
"""Debug V2: Full stealth test on morphllm.com/sign-up."""
import asyncio, sys
sys.path.insert(0, '/root/morph-worker')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox",
              "--disable-dev-shm-usage"],
    )
    
    viewport = {"width": 1440, "height": 900}
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    
    ctx = await browser.new_context(
        viewport=viewport, user_agent=ua, locale="en-US",
        timezone_id="Asia/Jakarta",
    )
    
    # Apply stealth
    stealth = Stealth()
    page = await ctx.new_page()
    try:
        await stealth.apply_stealth_async(ctx)
        print("Stealth applied successfully")
    except Exception as e:
        print(f"Stealth apply failed: {e}")
    await page.close()
    
    # Now navigate to sign-up
    page = await ctx.new_page()
    
    # Inject additional stealth manually
    await ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    """)
    
    await page.goto("https://morphllm.com/sign-up", wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)
    
    title = await page.title()
    url = page.url
    print(f"Title: {title}")
    print(f"URL: {url}")
    
    await page.screenshot(path="/tmp/morph_signup_v2.png", full_page=True)
    print("Screenshot: /tmp/morph_signup_v2.png")
    
    # Check for email input
    for sel in ['input[name="emailAddress"]', '#emailAddress-field', 'input[name="email"]']:
        try:
            el = page.locator(sel).first
            vis = await el.is_visible() if await el.count() > 0 else False
            print(f"  {sel}: count={await el.count()}, visible={vis}")
        except:
            print(f"  {sel}: ERROR")

    await browser.close()
    await pw.stop()

asyncio.run(main())
