"""
Runs the full apply flow across multiple accounts in ONE browser
session -- logout + Change user between accounts, same pattern as
login_all_test.py, instead of relaunching the browser each time.

Usage:
  python run_apply_multi.py TEMPSENS
"""

import sys
import time
from playwright.sync_api import sync_playwright
from decrypt_config import load_config
from human_behavior import (
    new_behavior_profile, human_delay, human_idle_before_switch,
    STEALTH_INIT_SCRIPT, STEALTH_CONTEXT_ARGS,
)
from login_test import login, logout
from apply_ipo import find_and_open_apply
from capture_application_id import capture_application_id
from application_log import log_application
from knowledge_base import diagnose_locally
import run_apply
from run_apply import fill_and_submit, DRY_RUN

TEST_ACCOUNT_LIMIT = 2  # set to None to run all accounts

if __name__ == "__main__":
    positional_args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    company_name = positional_args[0] if len(positional_args) > 0 and positional_args[0] else "TEMPSENS"
    quantity = positional_args[1] if len(positional_args) > 1 and positional_args[1] else None
    entered_upi_id = positional_args[2] if len(positional_args) > 2 and positional_args[2] else ""

    if "--live" in sys.argv:
        run_apply.DRY_RUN = False
        DRY_RUN = False
    elif "--dry-run" in sys.argv:
        run_apply.DRY_RUN = True
        DRY_RUN = True

    print(f"DRY_RUN is set to: {DRY_RUN}")

    if not entered_upi_id:
        if sys.stdin.isatty():
            entered_upi_id = input("Enter UPI ID to use for these applications: ").strip()
        else:
            entered_upi_id = "investor@okhdfcbank"
            print(f"Using default UPI ID (non-interactive): {entered_upi_id}")

    selected_accounts = []
    for i, arg in enumerate(sys.argv):
        if arg in ("--account", "--accounts") and i + 1 < len(sys.argv):
            selected_accounts = [acc.strip() for acc in sys.argv[i + 1].split(",") if acc.strip()]

    config = load_config()
    accounts = config["accounts"]

    if selected_accounts:
        filtered = [
            acc for acc in accounts
            if any(sel.lower() in acc.get("label", "").lower() for sel in selected_accounts)
        ]
        if filtered:
            accounts = filtered
            print(f"Target Account(s): {[a['label'] for a in accounts]}\n")
    elif TEST_ACCOUNT_LIMIT is not None:
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
            status = ""
            login_succeeded = False

            try:
                login_result = login(page, account, profile)
                if login_result is not True:
                    status = f"login_failed_{login_result}"
                    log_application(
                        account_label=account["label"], company=company_name,
                        status=status, upi_id=entered_upi_id, quantity=quantity or "",
                    )
                else:
                    login_succeeded = True
                    apply_result = find_and_open_apply(page, company_name, profile=profile)
                    captured = None
                    upi_id_to_log = entered_upi_id

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

                    if captured and captured.get("upi_id"):
                        upi_id_to_log = captured["upi_id"]

                    notes = ""
                    if captured and captured.get("created_on"):
                        notes = f"Originally applied: {captured['created_on']}"

                    log_application(
                        account_label=account["label"], company=company_name,
                        status=status,
                        application_id=(captured["application_id"] if captured else ""),
                        upi_id=upi_id_to_log, quantity=quantity or "",
                        notes=notes,
                    )
            except Exception as e:
                print(f"\nERROR on {account['label']}: {e}")
                try:
                    print(f"Current page URL: {page.url}")
                except Exception:
                    pass
                diagnose_locally(account["label"], f"applying for {company_name}", str(e))
                status = "error"
                log_application(
                    account_label=account["label"], company=company_name,
                    status=status, notes=str(e), upi_id=entered_upi_id, quantity=quantity or "",
                )

            results.append((account["label"], status))

            # Always log out this account before moving on -- whether
            # it's switching to the next account, or the final one
            # before the browser closes.
            if login_succeeded:
                try:
                    if i < len(accounts) - 1:
                        human_idle_before_switch(page, profile=profile)
                    logout(page, profile=profile)
                except Exception:
                    pass
                human_delay(1, 2)

        context.close()
        browser.close()

    print("\n=== SUMMARY ===")
    for label, status in results:
        print(f"  {label}: {status}")