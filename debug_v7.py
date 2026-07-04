#!/usr/bin/env python3
"""Debug V7: Screenshot right after signup to see landing page."""
import asyncio, sys, random
sys.path.insert(0, '/root/morph-worker')

from src.browser.signup import ClerkSignup

async def main():
    signup = ClerkSignup(headless=True, stealth=True, output_dir="/tmp/morph_debug")
    
    words = ["storm", "frost", "dawn", "shade", "ember", "coral", "sage", "onyx"]
    nouns = ["wolf", "hawk", "bear", "fox", "owl", "lynx", "orca", "puma"]
    email = f"{random.choice(words)}.{random.choice(nouns)}{random.randint(1,99)}@moyzel.foo"
    password = "Test1234!@#$"
    
    print(f"Email: {email}")
    
    # Get the page directly from signup
    page = await signup.new_page()
    
    # --- Copy modified _do_signup inline with screenshots ---
    from src.browser.signup import ClerkSignup as CS
    
    # Navigate
    await page.goto(CS.MORPH_URL, wait_until="domcontentloaded", timeout=30000)
    t = await page.title()
    print(f"Loaded: title='{t[:80]}'")
    
    # Wait for Vercel
    import asyncio as aio
    for i in range(15):
        await aio.sleep(2)
        title = await page.title()
        blocked = ["Attention Required", "Just a moment", "Vercel Security Checkpoint", "Checking your browser"]
        if not any(t in title for t in blocked):
            print(f"Vercel passed at t={(i+1)*2}s")
            break
    else:
        print("Vercel STUCK")
        await signup.close()
        return
    
    await page.wait_for_load_state("networkidle", timeout=20000)
    await aio.sleep(2)
    
    # Screenshot: what we see on homepage
    await page.screenshot(path="/tmp/morph_v7a_homepage.png")
    print("Screenshot: /tmp/morph_v7a_homepage.png")
    
    # Check if signup form is on homepage
    has_signup = "sign-up" in page.url or "signup" in page.url
    content = await page.content()
    has_clerk_signup = "cl-signUp" in content
    has_email_field = 'name="emailAddress"' in content or 'id="emailAddress"' in content
    print(f"Has signup URL: {has_signup}")
    print(f"Has Clerk SignUp component: {has_clerk_signup}")
    print(f"Has email input: {has_email_field}")
    
    # Find and click "Sign Up" or go to /sign-up
    if "/sign-up" not in page.url and "/signup" not in page.url:
        # Try clicking
        clicked = False
        for sel in ['a[href*="sign-up"]', 'a[href*="signup"]', 'button:has-text("Sign Up")', 'a:has-text("Sign Up")']:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible(timeout=2000):
                    print(f"Clicking {sel}...")
                    await el.click()
                    await aio.sleep(3)
                    clicked = True
                    break
            except:
                pass
        if not clicked:
            await page.goto(f"{CS.MORPH_URL}{CS.SIGNUP_PATH}", wait_until="domcontentloaded", timeout=20000)
            print(f"Navigated to /sign-up")
        await aio.sleep(2)
    
    # Screenshot: signup page
    await page.screenshot(path="/tmp/morph_v7b_signup_page.png")
    print("Screenshot: /tmp/morph_v7b_signup_page.png")
    print(f"URL: {page.url[:120]}")
    
    # Fill email
    from src.browser.signup import ClerkSignup as CS2
    for sel in CS2.EMAIL_SELECTORS:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible(timeout=2000):
                await el.click()
                await el.fill(email)
                print(f"Filled email via {sel}")
                break
        except:
            continue
    
    await aio.sleep(0.5)
    
    # Click Continue
    for sel in ['button[type="submit"]', '.cl-formButtonPrimary', 'button:has-text("Continue")']:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible(timeout=2000):
                await el.click()
                print(f"Clicked {sel}")
                break
        except:
            continue
    
    await aio.sleep(2)
    
    # Screenshot: after email continue
    await page.screenshot(path="/tmp/morph_v7c_after_email.png")
    print("Screenshot: /tmp/morph_v7c_after_email.png")
    
    # Fill password
    for sel in CS2.PASSWORD_SELECTORS:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible(timeout=2000):
                await el.click()
                await el.fill(password)
                print(f"Filled password via {sel}")
                break
        except:
            continue
    
    await aio.sleep(0.5)
    
    for sel in ['button[type="submit"]', 'button:has-text("Continue")', '.cl-formButtonPrimary']:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible(timeout=2000):
                await el.click()
                print(f"Clicked {sel}")
                break
        except:
            continue
    
    await aio.sleep(3)
    
    # Screenshot: after password submit
    await page.screenshot(path="/tmp/morph_v7d_after_password.png")
    print("Screenshot: /tmp/morph_v7d_after_password.png")
    print(f"URL: {page.url[:120]}")
    t = await page.title()
    print(f"Title: {t[:80]}")
    
    # Check for name fields
    for sel in ['input[name="firstName"]', '#firstName']:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible(timeout=2000):
                print(f"Name field visible, filling...")
                await el.fill("Dev")
                break
        except:
            continue
    
    for sel in ['input[name="lastName"]', '#lastName']:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible(timeout=2000):
                await el.fill("User")
                break
        except:
            continue
    
    for sel in ['button[type="submit"]', 'button:has-text("Continue")', '.cl-formButtonPrimary']:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible(timeout=2000):
                await el.click()
                print(f"Clicked {sel}")
                break
        except:
            continue
    
    await aio.sleep(5)
    
    # Screenshot: final state after signup
    await page.screenshot(path="/tmp/morph_v7e_final.png")
    print("Screenshot: /tmp/morph_v7e_final.png")
    print(f"URL: {page.url[:120]}")
    title = await page.title()
    print(f"Title: {title[:80]}")
    
    content = await page.content()
    has_dashboard = "dashboard" in page.url.lower()
    has_api = "api" in content.lower() and "key" in content.lower()
    has_signin = "sign-in" in content.lower() or "signIn" in content
    has_welcome = "welcome" in content.lower()
    has_clerk_user = "__clerk_db_jwt" in content or "clerk.session" in content.lower()
    
    print(f"\nFinal state:")
    print(f"  Dashboard URL: {has_dashboard}")
    print(f"  API key related: {has_api}")
    print(f"  Sign-in component: {has_signin}")
    print(f"  Welcome text: {has_welcome}")
    print(f"  Clerk session: {has_clerk_user}")
    
    await signup.close()

asyncio.run(main())
