"""
Local, private failure-diagnosis knowledge base for IPO BOT PRO.

- Never takes a screenshot.
- Never makes a network call of any kind.
- Never sends anything anywhere -- runs entirely on your own machine.

This recognizes patterns we've already solved together in chat. When
it doesn't recognize something, it says so plainly instead of
guessing -- bring that case back to chat, and once we solve it, we
add it here so the bot recognizes it next time.
"""

import re
import time
import json

DIAGNOSIS_LOG = "local_diagnosis_log.jsonl"

KNOWLEDGE_BASE = [
         {
        "keywords": ["cancel_failed", "apply_failed", "not found", "already_applied"],
        "diagnosis": "GENERAL PRINCIPLE, not just this bug: a function returning "
                      "None/False on a state check (already cancelled, already applied, "
                      "no row found) is easy to log as the same generic 'failed' as a "
                      "genuine error -- but 'already in the desired state' is a SUCCESS, "
                      "not a failure, and deserves its own distinct status.",
        "fix": "Before writing a new action function, ask: what does it mean if the "
               "thing I'm trying to do is ALREADY done? That outcome needs its own "
               "status (already_X), separate from a real failure -- don't let both "
               "collapse into one generic error label.",
    },

    {
        "keywords": ["networkidle", "timeout.*exceeded"],
        "diagnosis": "Kite's live price ticker means the network is never truly idle -- "
                      "a networkidle wait will hang until it times out.",
        "fix": "Use a fixed/randomized delay or wait for specific content instead of networkidle.",
    },
    {
        "keywords": ["wrong passphrase", "vault.key is corrupted"],
        "diagnosis": "The passphrase entered doesn't match the one used to create vault.key, "
                      "or vault.key/config.vault got corrupted or replaced.",
        "fix": "Re-enter the exact original passphrase. If truly lost, the vault cannot be "
               "recovered -- generate a new key and re-encrypt with your real account details.",
    },
    {
        "keywords": ["missing or has empty field", "yaml.*error", "problem_mark"],
        "diagnosis": "config.yaml has a missing field or a YAML formatting/indentation error "
                      "for one of the accounts.",
        "fix": "Open config.yaml, find the account and line number shown in the error, and fix "
               "the indentation or add the missing field -- every account needs exactly the "
               "same field structure and spacing.",
    },
    {
        "keywords": ["crucial_stop", "possibly important popup"],
        "diagnosis": "The bot found an unrecognized popup whose text matched a caution keyword "
                      "(like 'suspended', 'KYC', 'restricted') and stopped rather than guessing.",
        "fix": "Check crucial_popups.log for the exact popup text, log into that account "
               "manually to see what it's actually about, then decide whether to proceed.",
    },
    {
        "keywords": ["modulenotfounderror", "no module named"],
        "diagnosis": "A required Python file isn't in the project folder, or a package isn't "
                      "installed in this virtual environment.",
        "fix": "Confirm you're inside (venv) in CMD, and re-run: "
               "pip install playwright cryptography pyotp pyyaml",
    },
    {
        "keywords": ["permissionerror", "errno 13", "permission denied"],
        "diagnosis": "A file the bot needs to write to is open in another program (often Excel "
                      "locking a CSV file).",
        "fix": "Close the file in whatever program has it open, then re-run.",
    },
    {
        "keywords": ["strict mode violation", "resolved to.*elements"],
        "diagnosis": "A locator matched more than one element on the page.",
        "fix": "Scope the locator more narrowly -- by role, or to a specific row/container -- "
               "instead of plain text matching across the whole page.",
    },
    {
        "keywords": ["totp", "external totp.*timeout", "spinbutton.*not found"],
        "diagnosis": "The TOTP field wasn't found or didn't accept the code -- possibly the "
                      "page hadn't finished loading, or the code expired before it was entered.",
        "fix": "Ensure there's a short delay after the Login click before typing TOTP, and that "
               "TOTP uses human_type_totp (no typo simulation) since the code expires quickly.",
    },
]

def _matches(entry, text):
    text_lower = text.lower()
    return any(re.search(kw, text_lower) for kw in entry["keywords"])

def diagnose_locally(label, what_we_were_doing, error_message):
    """Checks the error against the local knowledge base. Never
    touches the network or sends anything anywhere. Returns True if a
    known pattern matched, False if this looks new."""
    combined = f"{what_we_were_doing} {error_message}"
    for entry in KNOWLEDGE_BASE:
        if _matches(entry, combined):
            print(f"\n[LOCAL DIAGNOSIS] Known pattern matched for {label}:")
            print(f"  DIAGNOSIS: {entry['diagnosis']}")
            print(f"  KNOWN FIX: {entry['fix']}")
            _log(label, what_we_were_doing, error_message, entry)
            return True

    print(f"\n[LOCAL DIAGNOSIS] No known pattern matched for {label} -- this looks new.")
    print("Bring this terminal output back to chat so we can solve it and add it here.")
    _log(label, what_we_were_doing, error_message, None)
    return False

def _log(label, what_we_were_doing, error_message, matched_entry):
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "account": label,
        "what_we_were_doing": what_we_were_doing,
        "error_message": error_message,
        "matched_known_pattern": matched_entry is not None,
        "diagnosis": matched_entry["diagnosis"] if matched_entry else None,
        "fix": matched_entry["fix"] if matched_entry else None,
    }
    with open(DIAGNOSIS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")