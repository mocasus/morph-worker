#!/usr/bin/env python3
"""Debug V8: Capture page state after auto-signin attempt."""
import asyncio, sys, json, os
sys.path.insert(0, '/root/morph-worker/src')

from browser.signup import ClerkSignup
from config import Config

OUT = '/tmp/morph_debug_v8'
os.makedirs(OUT, exist_ok=True)

CS = ClerkSignup  # alias

async def main():
    email = f"debugv8.test{random.randint(1000,9999)}@moyzel.foo"
    cfg = Config.load()
    password = cfg.default_password
    
    cs = ClerkSignup(headless=False, output_dir=OUT)
    await cs._launch()
    
    page = await cs.new_page()
    
    # ── Go to signup page ──
    await page.goto(CS.MORPH_URL, wait_until="domcontentloaded", timeout=30000)
    print(f"Homepage: title={await page.title()[:60]}, url={page.url[:80]}")
    
    # Click Sign Up
    await cs._click_first(page, [
        'a[href*="sign-up"]', 'text="Sign Up"', 'text="Get Started"',
    ], timeout=5000)
    await cs._human_delay(2, 3)
    print(f"After click signup: url={page.url[:80]}")
    
    # Fill email
    ok = await cs._fill_field(page, email, cs.EMAIL_SELECTORS, timeout=5000)
    print(f"Email filled: {ok}")
    await cs._human_delay(0.5, 1)
    ok = await cs._click_first(page, [
        'button[type="submit"]', 'button:has-text("Continue")', '.cl-formButtonPrimary',
    ], timeout=3000)
    print(f"Email continue: {ok}")
    await cs._human_delay(2, 4)
    
    # Fill password
    ok = await cs._fill_field(page, password, cs.PASSWORD_SELECTORS, timeout=5000)
    print(f"Password filled: {ok}")
    await cs._human_delay(0.5, 1)
    ok = await cs._click_first(page, [
        'button[type="submit"]', 'button:has-text("Continue")', '.cl-formButtonPrimary',
    ], timeout=3000)
    print(f"Password continue: {ok}")
    await cs._human_delay(3, 5)
    
    print(f"\nAfter signup: url={page.url[:80]}, title={await page.title()[:60]}")
    
    # ── Check sign-in presence ──
    is_signin = await cs._has_any(page, [
        '.cl-signIn-root', '.cl-signIn-start',
        'text="Sign in to your account"', 'text="Welcome back"',
        'h2:has-text("Sign in")', '[data-clerk-component="SignIn"]',
        'a[href*="sign-in"]',
    ], timeout=5000)
    print(f"SignIn component detected: {is_signin}")
    
    # ── Dump page structure ──
    body_html = await page.content()
    # Extract just relevant Clerk parts
    for marker in ['SignIn', 'sign-in', 'cl-formButtonPrimary', 'input']:
        lines = [l.strip() for l in body_html.split('\n') if marker.lower() in l.lower()]
        if lines:
            print(f"\n  [{marker}] {len(lines)} matches:")
            for l in lines[:5]:
                print(f"    {l[:200]}")
    
    # Screenshot
    await page.screenshot(path=f"{OUT}/after_signup.png", full_page=False)
    print(f"\nScreenshot: {OUT}/after_signup.png")
    
    # ── Try auto-signin manually ──
    print("\n--- Trying auto-signin ---")
    
    # Check if email field is visible
    email_visible = await cs._has_any(page, 
        ['input[name="email"]', 'input[type="email"]',
         '.cl-formFieldInput[type="email"]', 'input[id*="email"]'], timeout=3000)
    print(f"Email field visible: {email_visible}")
    
    # Check if password field is visible directly
    pw_visible = await cs._has_any(page,
        ['input[name="password"]', 'input[type="password"]'], timeout=3000)
    print(f"Password field visible: {pw_visible}")
    
    # Try filling email on sign-in form
    if email_visible:
        ok = await cs._fill_field(page, email, cs.EMAIL_SELECTORS, timeout=5000)
        print(f"Re-filled email: {ok}")
        await cs._human_delay(0.5, 1)
        ok = await cs._click_first(page, [
            'button[type="submit"]', 'button:has-text("Continue")', '.cl-formButtonPrimary',
        ], timeout=3000)
        print(f"Email continue clicked: {ok}")
        await cs._human_delay(2, 4)
        print(f"After email continue: url={page.url[:80]}")
    
    # Now fill password
    if pw_visible:
        ok = await cs._fill_field(page, password, cs.PASSWORD_SELECTORS, timeout=5000)
        print(f"Filled password: {ok}")
        await cs._human_delay(0.5, 1)
        ok = await cs._click_first(page, [
            'button[type="submit"]', 'button:has-text("Continue")',
            '.cl-formButtonPrimary', 'button:has-text("Sign In")',
        ], timeout=3000)
        print(f"Sign-in clicked: {ok}")
    
    # Wait for redirect
    await cs._human_delay(5, 8)
    print(f"Final URL: {page.url[:80]}")
    print(f"Final title: {await page.title()[:60]}")
    
    await page.screenshot(path=f"{OUT}/final_state.png", full_page=False)
    print(f"Screenshot: {OUT}/final_state.png")
    
    await cs.close()

import random
asyncio.run(main())
