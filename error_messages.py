"""
Translates internal status codes into clear, structured diagnostics
-- for both terminal output and future frontend display. Every
outcome gets a distinct code, a plain-English reason, and (where
possible) a concrete suggestion, instead of a generic 'failed'.
"""

DIAGNOSTICS = {
    "submitted": {
        "message": "Application submitted successfully.",
        "suggestion": None,
    },
    "dry_run": {
        "message": "Form filled successfully (dry run) -- nothing was actually submitted.",
        "suggestion": None,
    },
    "already_applied": {
        "message": "This account has already applied to this IPO.",
        "suggestion": None,
    },
    "not_applied_ipo_closed_or_old": {
        "message": "This IPO is not currently open, and no application record exists for it on this account.",
        "suggestion": "Check the exact company/symbol name matches Kite's listing exactly -- "
                       "a misspelling or wrong symbol produces this same result as a genuinely closed IPO.",
    },
    "apply_failed": {
        "message": "The IPO was found but couldn't be applied to right now.",
        "suggestion": "Check if it shows CLOSED, UPCOMING, or Pre-apply on the page -- "
                       "each has a different valid action window.",
    },
    "submit_not_found": {
        "message": "The application form opened, but the Submit button couldn't be found.",
        "suggestion": "Zerodha's form layout may have changed -- worth a fresh look at the live page.",
    },
    "cancel_failed": {
        "message": "Cancellation could not be completed.",
        "suggestion": "Check if it's outside the 10AM-4:45PM cancellation window, or already in a final state.",
    },
    "already_cancelled": {
        "message": "This application was already cancelled.",
        "suggestion": None,
    },
    "not_found": {
        "message": "No application record exists for this company on this account at all.",
        "suggestion": None,
    },
    "modify_failed": {
        "message": "Modification could not be completed.",
        "suggestion": "Check status is SUBMITTED (not PENDING), it's within the 10AM-4:45PM window, "
                       "and you haven't hit the 3-modification limit.",
    },
    "modify_validation_failed": {
        "message": "The requested quantity failed local validation before attempting Modify.",
        "suggestion": "See the specific reason in the notes -- likely not a lot-size multiple, or over the retail cap.",
    },
    "error": {
        "message": "An unexpected error occurred during the run.",
        "suggestion": "Check the notes field for the exact exception message and page URL.",
    },
}

def diagnose(status_code, company_name=""):
    """Returns a dict {code, message, suggestion} for any known
    status. Unknown codes get a plain fallback rather than crashing."""
    entry = DIAGNOSTICS.get(status_code)
    if entry is None:
        return {
            "code": status_code,
            "message": f"Unrecognized status '{status_code}' for {company_name}.",
            "suggestion": "This is a new outcome we haven't classified yet -- bring it back to chat.",
        }
    return {"code": status_code, "message": entry["message"], "suggestion": entry["suggestion"]}