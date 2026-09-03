import time
from playwright.sync_api import sync_playwright
from decrypt_config import load_config
from human_behavior import (
    new_behavior_profile, human_delay, human_idle_before_switch,
    STEALTH_INIT_SCRIPT, STEALTH_CONTEXT_ARGS,
)
from login_test import login, logout
from knowledge_base import diagnose_locally

# --- Quick test control -----------------------------------------
TEST_ACCOUNT_LIMIT = 2   # set to None to run all accounts
# ------------------------------------------------------------------

if __name__ == "__main__":
    config = load_config()
    accounts = config["accounts"]

    if TEST_ACCOUNT_LIMIT is not None:
        accounts = accounts[:TEST_ACCOUNT_LIMIT]
        print(f"[TEST MODE] Running only the first {TEST_ACCOUNT_LIMIT} account(s).\n")

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(**STEALTH_CONTEXT_ARGS)
        context.add_init_script(STEALTH_INIT_SCRIPT)
        page = context.new_page()

        for i, account in enumerate(accounts):
            profile = new_behavior_profile()

            try:
                result = login(page, account, profile)
                results.append((account["label"], result))
                if result == "crucial_stop":
                    diagnose_locally(account["label"], "logging in", "crucial_stop popup encountered")
                elif result is not True:
                    diagnose_locally(account["label"], "logging in", "login did not confirm the IPO page")
            except Exception as e:
                print(f"ERROR on {account['label']}: {e}")
                results.append((account["label"], False))
                diagnose_locally(account["label"], "logging in", str(e))

            if i < len(accounts) - 1:
                human_idle_before_switch(page, profile=profile)
                try:
                    logout(page, profile=profile)
                except Exception:
                    pass
                human_delay(1, 3)

        context.close()
        browser.close()

    print("\n=== SUMMARY ===")
    for label, result in results:
        if result is True:
            status = "OK"
        elif result == "crucial_stop":
            status = "STOPPED - check crucial_popups.log"
        else:
            status = "FAILED/UNCERTAIN"
        print(f"  {label}: {status}")