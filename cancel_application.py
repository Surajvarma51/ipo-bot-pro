"""
Cancels an existing IPO application, using the exact confirmed flow
from live recording: click the row's ellipsis -> click "Cancel" -> a
Confirm dialog appears -> click "Ok" to confirm (or "Cancel" to back
out).

Uses resilient_find with ranked fallback strategies for the key
clicks, so a small label/layout change on Zerodha's end doesn't
necessarily break this -- it tries the next-best approach on its own
and flags when it had to.

This module does the technical action only. The actual safety
confirmation (retyping the company name, re-entering the passphrase)
belongs in the calling script, not here.
"""

import re
from human_behavior import human_delay, resilient_find
from capture_application_id import capture_application_id

ACTIONABLE_STATUS = re.compile(r"SUBMITTED|PENDING", re.IGNORECASE)

def cancel_application(page, company_name, profile=None):
    before = capture_application_id(page, company_name)

    try:
        search_box = page.get_by_placeholder("Search table")
        if search_box.count() > 0:
            search_box.first.fill(company_name)
            human_delay(0.5, 1)
    except Exception:
        pass

    row = (
        page.locator("tr")
        .filter(has_text=company_name)
        .filter(has_text=ACTIONABLE_STATUS)
        .first
    )
    if row.count() == 0:
        print(f"No PENDING/SUBMITTED application found for '{company_name}' -- nothing to cancel.")
        return None

    row.hover()
    human_delay(0.3, 0.6)

    ellipsis, _ = resilient_find(page, [
        lambda: row.locator(".icon.icon-ellipsis"),
        lambda: row.locator('[class*="ellipsis"]'),
        lambda: row.get_by_role("button", name=re.compile("options|more|menu", re.IGNORECASE)),
        lambda: row.locator("button").last,
    ], description="row options icon")

    if ellipsis is None:
        return None

    ellipsis.first.click()
    human_delay(0.3, 0.6)

    cancel_link, _ = resilient_find(page, [
        lambda: page.get_by_role("link", name=" Cancel"),
        lambda: page.get_by_role("link", name="Cancel"),
        lambda: page.get_by_text("Cancel", exact=True),
        lambda: page.get_by_role("menuitem", name=re.compile("cancel", re.IGNORECASE)),
    ], description="Cancel menu option")

    if cancel_link is None:
        return None

    cancel_link.first.click()
    human_delay(0.5, 1)

    confirm_dialog = page.get_by_role("dialog")
    ok_button, _ = resilient_find(page, [
        lambda: confirm_dialog.get_by_role("button", name="Ok"),
        lambda: confirm_dialog.get_by_role("button", name=re.compile("^(ok|yes|confirm)$", re.IGNORECASE)),
        lambda: page.get_by_role("button", name=re.compile("^(ok|yes|confirm)$", re.IGNORECASE)),
    ], description="confirm Ok button")

    if ok_button is None:
        print("Confirm dialog did not appear as expected -- stopping without cancelling.")
        return None

    print(f"Confirm dialog appeared for {company_name} -- clicking Ok to confirm cancellation.")
    ok_button.first.click()
    human_delay(1, 2)

    after = capture_application_id(page, company_name)

    return {"before": before, "after": after}