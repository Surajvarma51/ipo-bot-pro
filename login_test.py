import time
import pyotp
from playwright.sync_api import sync_playwright
from decrypt_config import load_config
from human_behavior import (
    new_behavior_profile, human_delay, human_click, human_type,
    human_type_totp, handle_popup,
    STEALTH_INIT_SCRIPT, STEALTH_CONTEXT_ARGS,
)

def logout(page, profile=None):
    try:
        profile_link = page.get_by_role("link", name="User profile")
        if profile_link.count() > 0:
            human_click(profile_link.first, page=page, profile=profile)
            human_delay(0.3, 0.6)
            logout_link = page.get_by_role("link", name="Logout")
            if logout_link.count() > 0:
                human_click(logout_link.first, page=page, profile=profile)
                human_delay(0.5, 1)
    except Exception:
        pass  # best-effort -- if logout fails, closing the browser context is enough

def login(page, account, profile):
    print(f"Logging in: {account['label']} ({account['broker']})")

    page.goto("https://kite.zerodha.com/")
    human_delay(1, 2)

    change_user = page.get_by_text("Change user")
    if change_user.count() > 0:
        human_click(change_user.first, page=page, profile=profile)
        human_delay(0.5, 1)

    userid_field = page.get_by_role("textbox", name="Phone number or User ID")
    human_type(userid_field, account["client_id"], profile=profile)

    password_field = page.get_by_role("textbox", name="Password")
    human_type(password_field, account["password"], profile=profile)

    login_button = page.get_by_role("button", name="Login")
    human_click(login_button, page=page, profile=profile)
    human_delay(1.5, 2.5)

    totp = pyotp.TOTP(account["totp_secret"])
    code = totp.now()
    totp_field = page.get_by_role("spinbutton", name="External TOTP")
    human_type_totp(totp_field, code, profile=profile)

    human_delay(2, 3)

    # Check for a popup after login. If it's an unrecognized, possibly
    # crucial one, stop here, log out, and let the caller know --
    # don't guess and click through something that might matter.
    result = handle_popup(page, profile=profile, account_label=account["label"])
    if result == "crucial_stop":
        logout(page, profile=profile)
        return "crucial_stop"
    human_delay(0.5, 1)

    print(f"Landed on: {page.url}")

    bids_link = page.get_by_text("Bids", exact=True)
    if bids_link.count() > 0:
        human_click(bids_link.first, page=page, profile=profile)
        human_delay(0.8, 1.5)

    result = handle_popup(page, profile=profile, account_label=account["label"])
    if result == "crucial_stop":
        logout(page, profile=profile)
        return "crucial_stop"

    # Only click the IPO tab if Kite didn't already land there by
    # default -- clicking it again when already active was causing an
    # unnecessary extra tab interaction.
    if "bids/ipo" not in page.url:
        ipo_tab = page.get_by_text("IPO", exact=True)
        if ipo_tab.count() > 0:
            human_click(ipo_tab.first, page=page, profile=profile)
            human_delay(1, 2)
    print(f"Final URL: {page.url}")

    if "bids/ipo" in page.url:
        print(f"SUCCESS: {account['label']} reached the IPO page.")
        return True
    else:
        print(f"UNCERTAIN: didn't confirm the IPO page for {account['label']}. Check manually.")
        return False

if __name__ == "__main__":
    config = load_config()
    test_account = config["accounts"][0]
    profile = new_behavior_profile()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(**STEALTH_CONTEXT_ARGS)
        context.add_init_script(STEALTH_INIT_SCRIPT)
        page = context.new_page()

        login(page, test_account, profile)

        print("\nBrowser will stay open for 15 seconds so you can check it visually...")
        time.sleep(15)
        browser.close()