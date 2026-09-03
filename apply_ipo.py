import re
from human_behavior import human_click, human_delay, retry_action, resilient_find

OPEN_LIST_LABELS = re.compile(r"Apply|Pre-apply|Applied|CLOSED|UPCOMING", re.IGNORECASE)

def find_and_open_apply(page, company_name, profile=None):
    row = (
        page.locator("tr")
        .filter(has_text=company_name)
        .filter(has_text=OPEN_LIST_LABELS)
        .first
    )

    if row.count() == 0:
        print(f"'{company_name}' not found in the open IPO list.")
        return "check_history"

    already_applied = row.get_by_text("Applied", exact=True)
    if already_applied.count() > 0:
        print(f"{company_name}: this account already shows 'Applied'.")
        return "already_applied"

    apply_button = row.get_by_text("Apply", exact=True)
    used_pre_apply = False
    if apply_button.count() == 0:
        apply_button = row.get_by_text("Pre-apply", exact=True)
        if apply_button.count() > 0:
            used_pre_apply = True
            print(f"'{company_name}' is in the Pre-apply window (not yet officially open) -- proceeding.")

    if apply_button.count() == 0:
        print(f"'{company_name}' is listed but not currently applyable (CLOSED/UPCOMING) -- checking Applications history instead.")
        return "check_history"

    retry_action("Click Apply/Pre-apply", lambda: human_click(apply_button.first, page=page, profile=profile))
    human_delay(1, 2)
    print(f"Clicked {'Pre-apply' if used_pre_apply else 'Apply'} for {company_name}.")

    human_delay(1, 1.5)

    investor_link = None
    for _ in range(6):
        investor_link, _ = resilient_find(page, [
            lambda: page.get_by_role("link", name=" Individual investor"),
            lambda: page.get_by_role("link", name="Individual investor"),
            lambda: page.get_by_text("Individual investor", exact=False),
            lambda: page.locator("a", has_text="Individual investor"),
        ], description="Individual investor category option")
        if investor_link is not None:
            break
        human_delay(0.5, 1)

    if investor_link is not None:
        already_this_category = investor_link.first.locator("xpath=..").get_by_text("Applied", exact=True)
        if already_this_category.count() > 0:
            print("'Individual investor' category already shows 'Applied' for this account.")
            return "already_applied"

        human_click(investor_link.first, page=page, profile=profile)
        human_delay(1, 2)
        print("Clicked 'Individual investor' category.")
    else:
        print("No investor category dropdown shown -- IPO likely has a single category.")

    modal = page.get_by_text("Amount payable")
    try:
        modal.wait_for(state="visible", timeout=8000)
        print(f"Application form (Amount payable) opened successfully{' via Pre-apply' if used_pre_apply else ''}.")
        return True
    except Exception:
        print(f"'Amount payable' didn't appear yet for {company_name} -- retrying once before giving up...")
        human_delay(1, 2)
        try:
            retry_action(f"Click {'Pre-apply' if used_pre_apply else 'Apply'} again",
                         lambda: human_click(apply_button.first, page=page, profile=profile))
            modal.wait_for(state="visible", timeout=10000)
            print(f"Application form opened successfully on retry{' via Pre-apply' if used_pre_apply else ''}.")
            return True
        except Exception:
            print(f"No application form appeared for {company_name} after retry -- likely already applied.")
            return "already_applied"

if __name__ == "__main__":
    import sys
    import time
    from playwright.sync_api import sync_playwright
    from decrypt_config import load_config
    from human_behavior import new_behavior_profile, STEALTH_INIT_SCRIPT, STEALTH_CONTEXT_ARGS
    from login_test import login

    company_name = sys.argv[1] if len(sys.argv) > 1 else "TEMPSENS"

    config = load_config()
    account = config["accounts"][0]
    profile = new_behavior_profile()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(**STEALTH_CONTEXT_ARGS)
        context.add_init_script(STEALTH_INIT_SCRIPT)
        page = context.new_page()

        result = login(page, account, profile)
        if result is True:
            find_and_open_apply(page, company_name, profile=profile)

        print("\nBrowser will stay open for 20 seconds so you can check it visually...")
        time.sleep(20)
        browser.close()