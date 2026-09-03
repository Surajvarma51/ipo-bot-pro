"""
Full apply flow for one IPO, one account: find -> apply -> fill ->
(DRY RUN stops here, before Submit) -> capture Application ID/UPI/
quantity/price -> log to Excel -> logout.

DRY_RUN = True is the default and safe setting -- it fills the form
and stops right before the Submit button, so nothing is actually
applied. Only set it to False when you're ready to apply for real.
"""

import sys
import time
from playwright.sync_api import sync_playwright
from decrypt_config import load_config
from human_behavior import new_behavior_profile, human_delay, human_click, retry_action, STEALTH_INIT_SCRIPT, STEALTH_CONTEXT_ARGS
from login_test import login, logout
from apply_ipo import find_and_open_apply
from capture_application_id import capture_application_id
from application_log import log_application
from knowledge_base import diagnose_locally

DRY_RUN = True  # <-- keep this True until you're ready to apply for real

def fill_and_submit(page, quantity, upi_id, profile=None):
    if quantity:
        qty_input = page.locator("input").nth(0)
        qty_input.fill(str(quantity))

    upi_field = page.get_by_role("textbox", name="UPI ID")

    try:
        current_value = upi_field.input_value().strip().lower()
    except Exception:
        current_value = ""

    if current_value != upi_id.strip().lower():
        retry_action("Fill UPI ID", lambda: upi_field.fill(upi_id))

        amount_summary = page.locator(".amount-summary")
        if amount_summary.count() > 0:
            amount_summary.first.click()
            human_delay(0.3, 0.6)
    else:
        print("UPI ID field already matches -- no change needed.")

    human_delay(0.5, 1)

    if DRY_RUN:
        print("\n[DRY RUN] Form filled. Stopping BEFORE Submit -- nothing has been applied.")
        return "dry_run"

    submit_btn = page.get_by_role("button", name="Submit")
    if submit_btn.count() > 0:
        human_click(submit_btn.first, page=page, profile=profile)
        human_delay(2, 3)
        return "submitted"

    print("Could not find Submit button.")
    return "submit_not_found"

if __name__ == "__main__":
    positional_args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    company_name = positional_args[0] if len(positional_args) > 0 and positional_args[0] else "TEMPSENS"
    quantity = positional_args[1] if len(positional_args) > 1 and positional_args[1] else None
    entered_upi_id = positional_args[2] if len(positional_args) > 2 and positional_args[2] else ""

    if "--live" in sys.argv:
        DRY_RUN = False
    elif "--dry-run" in sys.argv:
        DRY_RUN = True

    print(f"DRY_RUN is set to: {DRY_RUN}")

    if not entered_upi_id:
        if sys.stdin.isatty():
            entered_upi_id = input("Enter UPI ID for this application: ").strip()
        else:
            entered_upi_id = "investor@okhdfcbank"
            print(f"Using default UPI ID (non-interactive): {entered_upi_id}")

    target_account_label = None
    for i, arg in enumerate(sys.argv):
        if arg in ("--account", "--accounts") and i + 1 < len(sys.argv):
            target_account_label = sys.argv[i + 1].split(",")[0].strip()

    config = load_config()
    account = config["accounts"][0]
    if target_account_label:
        matched = next((a for a in config["accounts"] if a.get("label") == target_account_label or target_account_label.lower() in a.get("label", "").lower()), None)
        if matched:
            account = matched
            print(f"Target Account: {account['label']}")

    profile = new_behavior_profile()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(**STEALTH_CONTEXT_ARGS)
        context.add_init_script(STEALTH_INIT_SCRIPT)
        page = context.new_page()

        login_succeeded = False

        try:
            login_result = login(page, account, profile)
            if login_result is not True:
                print(f"Login did not succeed cleanly ({login_result}) -- stopping.")
                log_application(
                    account_label=account["label"], company=company_name,
                    status=f"login_failed_{login_result}", upi_id=entered_upi_id,
                    quantity=quantity or "",
                )
            else:
                login_succeeded = True
                apply_result = find_and_open_apply(page, company_name, profile=profile)

                status = ""
                captured = None
                upi_id_to_log = entered_upi_id
                quantity_to_log = quantity or ""
                price_to_log = ""

                if apply_result is True:
                    status = fill_and_submit(page, quantity, entered_upi_id, profile=profile)
                elif apply_result == "already_applied":
                    status = "already_applied"
                elif apply_result == "check_history":
                    captured = capture_application_id(page, company_name)
                    if captured:
                        status = "already_applied"
                    else:
                        status = "not_applied_ipo_closed_or_old"
                else:
                    status = "apply_failed"

                if status in ("submitted", "already_applied") and captured is None:
                    captured = capture_application_id(page, company_name)

                if captured:
                    if captured.get("upi_id"):
                        upi_id_to_log = captured["upi_id"]
                    # Prefer the REAL applied quantity/price read back
                    # from Zerodha's own confirmation dialog over any
                    # CLI override -- this is what was actually applied.
                    if captured.get("quantity"):
                        quantity_to_log = captured["quantity"]
                    if captured.get("price"):
                        price_to_log = captured["price"]

                notes = ""
                if captured and captured.get("created_on"):
                    notes = f"Originally applied: {captured['created_on']}"

                log_application(
                    account_label=account["label"], company=company_name,
                    status=status,
                    application_id=(captured["application_id"] if captured else ""),
                    upi_id=upi_id_to_log,
                    quantity=quantity_to_log,
                    price=price_to_log,
                    notes=notes,
                )
        except Exception as e:
            print(f"\nERROR: {e}")
            try:
                print(f"Current page URL: {page.url}")
            except Exception:
                print("(could not read page URL -- page/browser may have crashed)")

            diagnose_locally(account["label"], f"applying for {company_name}", str(e))

            log_application(
                account_label=account["label"], company=company_name,
                status="error", notes=str(e), upi_id=entered_upi_id,
                quantity=quantity or "",
            )

        if login_succeeded:
            print("\nLogging out...")
            try:
                logout(page, profile=profile)
            except Exception as e:
                print(f"Logout may not have completed cleanly: {e}")

        print("Browser will stay open for 10 seconds so you can check it visually...")
        time.sleep(10)
        browser.close()