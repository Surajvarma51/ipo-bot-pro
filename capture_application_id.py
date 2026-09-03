"""
Captures the status, Application ID, UPI ID, original apply date,
quantity, and price from Kite's Applications list -- in a single
pass, no page reloads (a reload retry loop was causing more problems
than it solved, including a session drop).

Status and date come straight from the row itself (cheap, reliable),
so they're captured even if opening the Info dialog fails entirely.
Application ID/UPI/quantity/price come from the dialog, if it opens.
"""

import re
from human_behavior import human_delay, resilient_find

def capture_application_id(page, company_name, max_attempts=1):
    status_pattern = re.compile(r"SUBMITTED|PENDING|ALLOTTED|NOT ALLOTTED|CANCELLED", re.IGNORECASE)
    date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?")

    try:
        page.keyboard.press("Escape")
        human_delay(0.3, 0.5)

        toast_close = page.locator(".icon.icon-times.close")
        if toast_close.count() > 0:
            toast_close.first.click()
            human_delay(0.3, 0.5)

        page.keyboard.press("End")
        human_delay(0.8, 1.2)
    except Exception:
        pass

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
        .filter(has_text=status_pattern)
        .first
    )

    if row.count() == 0:
        print(f"  '{company_name}' not found in Applications history -- likely never applied, and this IPO is closed/old.")
        return None

    row_text = row.inner_text()
    status_match = status_pattern.search(row_text)
    status_text = status_match.group(0).upper() if status_match else None
    date_match = date_pattern.search(row_text)
    created_on = date_match.group(0) if date_match else None

    result = {
        "status": status_text,
        "created_on": created_on,
        "application_id": None,
        "upi_id": None,
        "quantity": None,
        "price": None,
    }

    try:
        row.hover()
        human_delay(0.3, 0.6)

        ellipsis, _ = resilient_find(page, [
            lambda: row.locator(".icon.icon-ellipsis"),
            lambda: row.locator('[class*="ellipsis"]'),
            lambda: row.get_by_role("button", name=re.compile("options|more|menu", re.IGNORECASE)),
            lambda: row.locator("button").last,
        ], description="row options icon")

        if ellipsis is not None:
            ellipsis.first.click()
            human_delay(0.3, 0.6)

            dialog_link, _ = resilient_find(page, [
                lambda: page.get_by_text("Info", exact=True),
                lambda: page.get_by_text("Submitted", exact=True),
                lambda: page.get_by_text("Pending", exact=True),
                lambda: page.get_by_text("Applied", exact=True),
                lambda: page.get_by_text("Not Allotted", exact=True),
                lambda: page.get_by_text("Allotted", exact=True),
                lambda: page.get_by_text("Cancelled", exact=True),
                lambda: page.get_by_text("Rejected", exact=True),
            ], description="dialog-opening menu link")

            if dialog_link is not None:
                dialog_link.first.click()
                human_delay(0.5, 1)

                dialog = page.locator('[role="dialog"]').first
                dialog.wait_for(state="visible", timeout=6000)
                dialog_text = dialog.inner_text()

                id_match = re.search(r"Application ID\s*\n?\s*([A-Za-z0-9]+)", dialog_text)
                upi_match = re.search(r"UPI ID\s*\n?\s*([\w.\-]+@[\w.\-]+)", dialog_text)
                created_match = re.search(r"Created on\s*\n?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", dialog_text)
                bids_match = re.search(r"Quantity\s*Price[^\n]*\n\s*(\d+)\s+(\d+)", dialog_text)

                close_btn = page.get_by_role("button", name="Close")
                if close_btn.count() > 0:
                    close_btn.first.click()

                result["application_id"] = id_match.group(1) if id_match else None
                result["upi_id"] = upi_match.group(1) if upi_match else None
                if created_match:
                    result["created_on"] = created_match.group(1)
                result["quantity"] = bids_match.group(1) if bids_match else None
                result["price"] = bids_match.group(2) if bids_match else None
    except Exception as e:
        print(f"  Could not open Info dialog: {e} -- returning status/date only.")

    if not result["application_id"]:
        print(f"  Application ID not captured this pass (status: {result['status']}). Check Kite directly if needed.")

    return result