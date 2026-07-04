#!/usr/bin/env python3
"""Debug V5: Full signup + API key screen inspection."""
import asyncio, sys, json
sys.path.insert(0, '/root/morph-worker')

from src.browser.signup import ClerkSignup

async def main():
    signup = ClerkSignup(headless=True, stealth=True, output_dir="/tmp/morph_debug")
    
    inbox = create_inbox()
    email = inbox.email
    password = "Test1234!@#$"
    
    print(f"Email: {email}")
    print(f"Password: {password}")
    
    # Do signup
    result = await signup.signup(email=email, password=password, 
                                  first_name="Dev", last_name="User")
    print(f"\nSignup result: {json.dumps(result, indent=2)}")
    
    if result.get("success"):
        print("\n--- Extracting API key ---")
        key_result = await signup.extract_api_key()
        print(f"Extract result: {json.dumps(key_result, indent=2)}")
    else:
        # Take screenshot of current state
        page = await signup.new_page()
        await page.goto("https://morphllm.com/dashboard/api-keys", 
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/morph_v5_dashboard.png")
        print("Screenshot: /tmp/morph_v5_dashboard.png")
        
        # Check page content
        title = await page.title()
        url = page.url
        print(f"Dashboard: title='{title}', url={url[:100]}")
        
        # Check if there's API key-related content
        content = await page.content()
        has_morph = "morph_" in content
        has_api = "api" in content.lower() and "key" in content.lower()
        print(f"  has morph_ key: {has_morph}")
        print(f"  has 'api key' text: {has_api}")
        
        # Check if logged in or redirected
        if "sign-in" in url.lower() or "login" in url.lower() or "sign-up" in url.lower():
            print("  ⚠️ Redirected to auth page — not logged in!")
        
        await page.close()
    
    await signup.close()

def create_inbox():
    """Simple catch-all inbox."""
    import random, string
    words = ["storm", "frost", "dawn", "shade", "ember", "coral", "sage", "onyx", 
             "polar", "lunar", "solar", "nova", "void", "flux", "zen"]
    nouns = ["wolf", "hawk", "bear", "fox", "owl", "lynx", "orca", "puma",
             "peak", "reef", "tide", "wind", "star", "moon", "wave"]
    name = f"{random.choice(words)}.{random.choice(nouns)}{random.randint(1,99)}"
    return SimpleInbox(f"{name}@moyzel.foo")

class SimpleInbox:
    def __init__(self, email):
        self.email = email
        self.meta = {"provider": "catchall", "domain": "moyzel.foo"}

asyncio.run(main())
