"""
Modifies the quantity on an existing SUBMITTED application (Modify is
NOT available for PENDING status -- only Cancel is). Only quantity
can be changed, never UPI ID. Modifying triggers a fresh UPI mandate
that needs accepting again. Zerodha allows a maximum of 3
modifications per application, exchange-mandated -- this isn't
readable from the page, so check applications_log.xlsx history
before running this.

Uses resilient_find with ranked fallback strategies for the key
clicks, so a small label/layout change on Zerodha's end doesn't
necessarily break this.
"""

import re
from human_behavior import human_delay, resilient_find
from capture_application_id import capture_application_id
from lot_calculator import validate_quantity

def modify_application(page, company_name, new_quantity, lot_size=None, cutoff_price=None, profile=None):
    before = capture_application_id(page, company_name)

    print(f"Reminder: Zerodha allows a maximum of 3 modifications per application. "
          f"Check applications_log.xlsx for {company_name}'s modify history before proceeding.")

    if lot_size and cutoff_price:
        valid, reason = validate_quantity(new_quantity, lot_size, cutoff_price)
        if not valid:
            print(f"Quantity validation failed: {reason}")
            return {"before": before, "after": None, "error": reason}

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
        .filter(has_text=re.compile("SUBMITTED", re.IGNORECASE))
        .first
    )
    if row.count() == 0:
        print(f"No SUBMITTED application found for '{company_name}' -- Modify only works on SUBMITTED, not PENDING.")
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

    modify_link, _ = resilient_find(page, [
        lambda: page.get_by_role("link", name=" Modify"),
        lambda: page.get_by_role("link", name="Modify"),
        lambda: page.get_by_text("Modify", exact=True),
        lambda: page.get_by_role("menuitem", name=re.compile("modify", re.IGNORECASE)),
    ], description="Modify menu option")

    if modify_link is None:
        return None

    modify_link.first.click()
    human_delay(0.5, 1)

    qty_field, _ = resilient_find(page, [
        lambda: page.get_by_role("spinbutton", name="Qty."),
        lambda: page.get_by_role("spinbutton", name=re.compile("qty|quantity", re.IGNORECASE)),
        lambda: page.locator("input[type='number']").first,
    ], description="Quantity field")

    if qty_field is None:
        return None

    qty_field.first.fill(str(new_quantity))
    human_delay(0.3, 0.6)

    submit_btn, _ = resilient_find(page, [
        lambda: page.get_by_role("button", name="Modify"),
        lambda: page.get_by_role("button", name=re.compile("^(modify|save|update)$", re.IGNORECASE)),
    ], description="Modify submit button")

    if submit_btn is None:
        return None

    submit_btn.first.click()
    human_delay(1, 2)

    after = capture_application_id(page, company_name)

    return {"before": before, "after": after}