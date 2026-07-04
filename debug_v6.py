#!/usr/bin/env python3
"""Debug V6: Test extract_api_key with existing session."""
import asyncio, sys, json, random, re
sys.path.insert(0, '/root/morph-worker')

from src.browser.signup import ClerkSignup

class SimpleInbox:
    def __init__(self, email):
        self.email = email
        self.meta = {"provider": "catchall", "domain": "moyzel.foo"}

async def main():
    signup = ClerkSignup(headless=True, stealth=True, output_dir="/tmp/morph_debug")
    
    words = ["storm", "frost", "dawn", "shade", "ember", "coral", "sage", "onyx"]
    nouns = ["wolf", "hawk", "bear", "fox", "owl", "lynx", "orca", "puma"]
    email = f"{random.choice(words)}.{random.choice(nouns)}{random.randint(1,99)}@moyzel.foo"
    password = "Test1234!@#$"
    
    print(f"Email: {email}")
    
    # Do signup
    result = await signup.signup(email=email, password=password, 
                                  first_name="Dev", last_name="User")
    print(f"Signup: success={result.get('success')}, state={result.get('state')}")
    
    # DEBUG: Navigate dashboard manually
    page = await signup.new_page()
    
    # Try dashboard first
    print("\n--- Navigating to /dashboard ---")
    await page.goto("https://morphllm.com/dashboard", 
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(4)
    title = await page.title()
    url = page.url
    print(f"Dashboard: title='{title}', url={url[:120]}")
    await page.screenshot(path="/tmp/morph_v6_dashboard.png")
    
    # Check what's on the page
    content = await page.content()
    # Print interesting parts
    for keyword in ["API Key", "api-key", "api_key", "morph_", "Create", "key", "Dashboard"]:
        count = content.lower().count(keyword.lower())
        if count > 0:
            print(f"  '{keyword}' found: {count} times")
    
    # Try clicking around
    print("\n--- Looking for API Keys link ---")
    for sel in ['a[href*="api-keys"]', 'a[href*="api-key"]', 'a:has-text("API")',
                'button:has-text("API")', 'button:has-text("Create")',
                'a[href*="settings"]', 'a[href*="dashboard"]']:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                text = await el.text_content() if await el.count() > 0 else ""
                visible = await el.is_visible(timeout=2000) if await el.count() > 0 else False
                print(f"  {sel}: count={await el.count()}, text='{text[:60]}', visible={visible}")
        except Exception as e:
            pass
    
    # Try /dashboard/api-keys directly
    print("\n--- Navigating to /dashboard/api-keys ---")
    await page.goto("https://morphllm.com/dashboard/api-keys", 
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(4)
    title = await page.title()
    url = page.url
    print(f"API Keys: title='{title}', url={url[:120]}")
    await page.screenshot(path="/tmp/morph_v6_apikeys.png")
    
    content = await page.content()
    for keyword in ["API Key", "api-key", "api_key", "morph_", "Create", "key", "No API"]:
        count = content.lower().count(keyword.lower())
        if count > 0:
            print(f"  '{keyword}' found: {count} times")
    
    # Print a snippet of the body HTML
    body_start = content.find("<body")
    if body_start > 0:
        snippet = content[body_start:body_start+2000]
        print(f"\n  Body snippet:\n{snippet[:1000]}")
    
    await signup.close()

asyncio.run(main())
