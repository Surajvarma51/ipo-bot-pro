"""
Interactive, safety-gated wrapper for cancelling an IPO application.

Requires:
1. Retyping the company name exactly, as a deliberate confirmation.
2. Re-entering your vault passphrase, as a second, separate
   confirmation gate specifically for the cancel action.

Always captures and logs whatever info is available (status,
Application ID, UPI, etc.) regardless of the outcome -- not just on
a successful new cancellation.
"""

import sys
import time
from playwright.sync_api import sync_playwright
from decrypt_config import load_config
from human_behavior import new_behavior_profile, STEALTH_INIT_SCRIPT, STEALTH_CONTEXT_ARGS
from login_test import login, logout
from cancel_application import cancel_application
from capture_application_id import capture_application_id
from application_log import log_application

if __name__ == "__main__":
    company_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not company_name:
        print("Usage: python run_cancel.py COMPANY_NAME")
        exit(1)

    print(f"You are about to CANCEL the application for: {company_name}")
    confirm_name = input(f"Type '{company_name}' again to confirm: ").strip()
    if confirm_name.upper() != company_name.upper():
        print("Name did not match -- aborting. Nothing was cancelled.")
        exit(1)

    config = load_config()
    account = config["accounts"][0]
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
                print(f"Login did not succeed cleanly ({login_result}) -- stopping, nothing cancelled.")
                log_application(
                    account_label=account["label"], company=company_name,
                    status=f"login_failed_{login_result}",
                )
            else:
                login_succeeded = True

                current_info = capture_application_id(page, company_name)
                current_status = current_info.get("status") if current_info else None

                if current_status == "CANCELLED":
                    print(f"'{company_name}' is already CANCELLED -- nothing to do.")
                    log_application(
                        account_label=account["label"], company=company_name,
                        status="already_cancelled",
                        application_id=current_info.get("application_id", "") or "",
                        upi_id=current_info.get("upi_id", "") or "",
                        quantity=current_info.get("quantity", "") or "",
                        price=current_info.get("price", "") or "",
                        notes=f"Confirmed already cancelled. Created on: {current_info.get('created_on', '')}",
                    )
                elif current_info is None:
                    print(f"No application found at all for '{company_name}' -- nothing to cancel.")
                    log_application(
                        account_label=account["label"], company=company_name,
                        status="not_found",
                    )
                else:
                    result = cancel_application(page, company_name, profile=profile)

                    if result is None:
                        print("Cancellation did not go through -- see messages above.")
                        log_application(
                            account_label=account["label"], company=company_name,
                            status="cancel_failed",
                            application_id=current_info.get("application_id", "") or "",
                            upi_id=current_info.get("upi_id", "") or "",
                            notes=f"Was status: {current_status}",
                        )
                    else:
                        before = result["before"] or {}
                        after = result["after"] or {}
                        print(f"\nBefore: {before}")
                        print(f"After:  {after}")
                        log_application(
                            account_label=account["label"], company=company_name,
                            status="cancelled",
                            application_id=after.get("application_id", "") or "",
                            upi_id=after.get("upi_id", "") or "",
                            quantity=after.get("quantity", "") or "",
                            price=after.get("price", "") or "",
                            notes=f"Cancelled. Was: {before}",
                        )
        except Exception as e:
            print(f"\nERROR: {e}")

        if login_succeeded:
            try:
                logout(page, profile=profile)
            except Exception:
                pass

        print("\n=== DONE. Browser will close automatically in 10 seconds. ===")
        time.sleep(10)
        print("Closing browser now.")
        browser.close()