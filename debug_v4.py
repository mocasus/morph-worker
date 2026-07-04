#!/usr/bin/env python3
"""Debug V4: Test using the actual ClerkSignup class to isolate the issue."""
import asyncio, sys
sys.path.insert(0, '/root/morph-worker')

from src.browser.signup import ClerkSignup

async def main():
    signup = ClerkSignup(headless=True, stealth=True, output_dir="/tmp/morph_debug")
    
    # Manually launch + new_page (same as signup flow)
    page = await signup.new_page()
    print(f"Page created: {page}")
    print(f"Browser: {signup.browser}")
    print(f"Context: {signup.context}")
    
    # Navigate exactly like debug_v3
    print("\nNavigating to morphllm.com...")
    await page.goto("https://morphllm.com", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)
    
    # Check JS execution
    try:
        result = await page.evaluate("() => document.title")
        print(f"JS title: {result}")
        result = await page.evaluate("() => navigator.userAgent")
        print(f"JS UA: {result[:60]}")
        result = await page.evaluate("() => navigator.webdriver")
        print(f"JS webdriver: {result}")
    except Exception as e:
        print(f"JS eval error: {e}")
    
    # Check title multiple times
    for i in range(5):
        await asyncio.sleep(2)
        title = await page.title()
        print(f"  t={2*(i+1)}s: title='{title[:80]}'")
        if "Vercel" not in title:
            print("  → PASSED!")
            break
    
    await page.screenshot(path="/tmp/morph_signup_v4.png")
    print("Screenshot: /tmp/morph_signup_v4.png")
    
    await signup.close()

asyncio.run(main())
