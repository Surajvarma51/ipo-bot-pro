"""
Interactive, safety-gated wrapper for modifying an IPO application's
quantity. Modify only works on SUBMITTED status (not PENDING), and
only quantity can be changed -- never UPI ID.

Requires retyping the company name to confirm, plus your vault
passphrase, before anything is clicked.
"""

import re
import sys
import time
from playwright.sync_api import sync_playwright
from decrypt_config import load_config
from human_behavior import new_behavior_profile, STEALTH_INIT_SCRIPT, STEALTH_CONTEXT_ARGS
from login_test import login, logout
from modify_application import modify_application
from capture_application_id import capture_application_id
from application_log import log_application
from lot_calculator import parse_ipo_row_info

OPEN_LIST_LABELS = re.compile(r"Apply|Applied|Pre-apply|CLOSED|UPCOMING", re.IGNORECASE)

def find_lot_and_cutoff(page, company_name):
    try:
        row = (
            page.locator("tr")
            .filter(has_text=company_name)
            .filter(has_text=OPEN_LIST_LABELS)
            .first
        )
        if row.count() > 0:
            return parse_ipo_row_info(row.inner_text())
    except Exception:
        pass
    return None, None, None

if __name__ == "__main__":
    company_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not company_name:
        print("Usage: python run_modify.py COMPANY_NAME")
        exit(1)

    print(f"You are about to MODIFY the application for: {company_name}")
    confirm_name = input(f"Type '{company_name}' again to confirm: ").strip()
    if confirm_name.upper() != company_name.upper():
        print("Name did not match -- aborting. Nothing was modified.")
        exit(1)

    new_quantity = input("Enter the new quantity (must be a multiple of the lot size): ").strip()
    if not new_quantity.isdigit():
        print("Quantity must be a whole number -- aborting.")
        exit(1)
    new_quantity = int(new_quantity)

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
                print(f"Login did not succeed cleanly ({login_result}) -- stopping, nothing modified.")
                log_application(
                    account_label=account["label"], company=company_name,
                    status=f"login_failed_{login_result}",
                )
            else:
                login_succeeded = True

                lot_size, price_low, price_high = find_lot_and_cutoff(page, company_name)
                cutoff_price = price_high
                if lot_size and cutoff_price:
                    print(f"Found lot size {lot_size}, cutoff price {cutoff_price} -- validating locally.")
                else:
                    print("Could not read lot size/price from the open list -- proceeding without local validation.")

                result = modify_application(
                    page, company_name, new_quantity,
                    lot_size=lot_size, cutoff_price=cutoff_price, profile=profile
                )

                if result is None:
                    print("Modification did not go through -- see messages above.")
                    log_application(
                        account_label=account["label"], company=company_name,
                        status="modify_failed",
                    )
                elif result.get("error"):
                    print(f"Modification blocked by validation: {result['error']}")
                    log_application(
                        account_label=account["label"], company=company_name,
                        status="modify_validation_failed",
                        notes=result["error"],
                    )
                else:
                    before = result["before"] or {}
                    after = result["after"] or {}
                    print(f"\nBefore: {before}")
                    print(f"After:  {after}")
                    log_application(
                        account_label=account["label"], company=company_name,
                        status="modified",
                        application_id=after.get("application_id", "") or "",
                        upi_id=after.get("upi_id", "") or "",
                        quantity=after.get("quantity", "") or str(new_quantity),
                        price=after.get("price", "") or "",
                        notes=f"Modified. Was: {before}",
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