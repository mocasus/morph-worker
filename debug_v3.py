#!/usr/bin/env python3
"""Debug V3: Navigate homepage first to get Vercel cookie, then signup."""
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
    tmp_page = await ctx.new_page()
    try:
        await stealth.apply_stealth_async(ctx)
        print("Stealth applied successfully")
    except Exception as e:
        print(f"Stealth apply failed: {e}")
    await tmp_page.close()
    
    # Step 1: Visit homepage — let Vercel challenge run and resolve
    page = await ctx.new_page()
    print("Step 1: Visiting morphllm.com homepage...")
    await page.goto("https://morphllm.com", wait_until="domcontentloaded", timeout=30000)
    
    # Wait for Vercel challenge (try waiting for page to change)
    for i in range(15):
        await asyncio.sleep(2)
        title = await page.title()
        url = page.url
        print(f"  t={i*2}s: title='{title[:50]}' url={url[:60]}")
        if "Attention" not in title and "Vercel" not in title and "Checking" not in title:
            print(f"  → Challenge passed at t={i*2}s!")
            break
    
    # Check if any Clerk content appeared
    for sel in ['input[name="emailAddress"]', '.cl-formFieldInput', 'a[href*="sign-up"]']:
        try:
            el = page.locator(sel).first
            c = await el.count()
            print(f"  {sel}: count={c}")
        except:
            pass
    
    await page.screenshot(path="/tmp/morph_v3_home.png", full_page=True)
    print("Screenshot homepage: /tmp/morph_v3_home.png")
    
    # Step 2: Navigate to signup with the Vercel cookie
    print("\nStep 2: Navigating to /sign-up...")
    await page.goto("https://morphllm.com/sign-up", wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)
    
    title = await page.title()
    url = page.url
    print(f"Title: {title}")
    print(f"URL: {url}")
    
    await page.screenshot(path="/tmp/morph_v3_signup.png", full_page=True)
    print("Screenshot signup: /tmp/morph_v3_signup.png")
    
    # Check for email input
    for sel in ['input[name="emailAddress"]', '#emailAddress-field', '.cl-formFieldInput', 'input[name="email"]']:
        try:
            el = page.locator(sel).first
            vis = await el.is_visible() if await el.count() > 0 else False
            print(f"  {sel}: count={await el.count()}, visible={vis}")
        except Exception as e:
            print(f"  {sel}: ERROR - {e}")
    
    await browser.close()
    await pw.stop()

asyncio.run(main())
