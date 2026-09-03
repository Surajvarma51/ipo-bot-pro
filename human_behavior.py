import random
import time

def human_delay(min_s=0.4, max_s=1.2):
    time.sleep(random.uniform(min_s, max_s))

def new_behavior_profile():
    return {
        "typing_min": random.uniform(50, 90),
        "typing_max": random.uniform(140, 220),
    }

def human_move_to(page, x, y, profile=None, steps=None):
    page.mouse.move(x, y, steps=1)

def human_click(locator, page=None, profile=None):
    box = locator.bounding_box()
    if box and page:
        target_x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
        target_y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
        human_move_to(page, target_x, target_y, profile=profile)
        human_delay(0.1, 0.3)
    locator.click()
    human_delay(0.2, 0.5)

def human_type(locator, text, profile=None):
    locator.click()
    human_delay(0.1, 0.3)
    typing_min = profile["typing_min"] if profile else 60
    typing_max = profile["typing_max"] if profile else 180

    if text.isdigit():
        typo_pool = "0123456789"
    elif text.isalpha():
        typo_pool = "abcdefghijklmnopqrstuvwxyz"
    else:
        typo_pool = "abcdefghijklmnopqrstuvwxyz0123456789"

    typed_so_far = ""
    for char in text:
        if random.random() < 0.06 and len(typed_so_far) > 0:
            wrong_char = random.choice(typo_pool)
            locator.type(wrong_char, delay=random.uniform(typing_min, typing_max))
            human_delay(0.15, 0.45)
            r = random.random()
            if r < 0.6:
                backspace_count = 1
            elif r < 0.9:
                backspace_count = random.randint(2, 3)
            else:
                backspace_count = len(typed_so_far) + 1
            for _ in range(backspace_count):
                locator.press("Backspace", delay=random.uniform(typing_min * 0.5, typing_max * 0.5))
            keep = max(0, len(typed_so_far) - (backspace_count - 1))
            retyped = typed_so_far[keep:]
            typed_so_far = typed_so_far[:keep]
            for rc in retyped:
                locator.type(rc, delay=random.uniform(typing_min, typing_max))
                typed_so_far += rc
        locator.type(char, delay=random.uniform(typing_min, typing_max))
        typed_so_far += char
    human_delay(0.2, 0.5)

def human_type_totp(locator, text, profile=None):
    locator.click()
    human_delay(0.1, 0.2)
    typing_min = profile["typing_min"] if profile else 60
    typing_max = profile["typing_max"] if profile else 180
    for char in text:
        locator.type(char, delay=random.uniform(typing_min, typing_max))

def retry_action(description, fn, attempts=3, delay_s=2):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e
            if attempt < attempts:
                print(f"  '{description}' failed (attempt {attempt}/{attempts}): "
                      f"{type(e).__name__} -- retrying in {delay_s}s...")
                time.sleep(delay_s)
            else:
                print(f"  '{description}' failed after {attempts} attempts, giving up.")
    raise last_error

CRUCIAL_POPUP_KEYWORDS = [
    "suspend", "blocked", "restrict", "unauthorized", "fraud", "locked",
    "kyc", "compliance", "penalty", "freeze", "frozen", "deactivat",
    "account disabled", "verify your account", "action required",
]

def _check_popup_once(page, profile=None, account_label=""):
    dismiss_labels = ["I understand", "Got it", "OK", "Close", "Continue", "I agree"]
    for label in dismiss_labels:
        btn = page.get_by_role("button", name=label)
        if btn.count() > 0:
            try:
                human_click(btn.first, page=page, profile=profile)
                human_delay(0.3, 0.6)
            except Exception:
                pass
            return "dismissed"

    dialog = page.locator('[role="dialog"]').first
    if dialog.count() > 0:
        try:
            if not dialog.is_visible():
                return "none"
            box = dialog.bounding_box()
            viewport = page.viewport_size
            if box and viewport:
                covers_most_of_screen = (
                    box["width"] > viewport["width"] * 0.85
                    and box["height"] > viewport["height"] * 0.85
                )
                if covers_most_of_screen:
                    return "none"
            popup_text = dialog.inner_text().strip()
        except Exception:
            popup_text = ""

        if popup_text and len(popup_text) < 400:
            lowered = popup_text.lower()
            if any(word in lowered for word in CRUCIAL_POPUP_KEYWORDS):
                print(f"\n[STOPPED] Unrecognized, possibly important popup on {account_label}:")
                print(popup_text)
                with open("crucial_popups.log", "a", encoding="utf-8") as f:
                    f.write(f"--- {account_label} ---\n{popup_text}\n\n")
                return "crucial_stop"

            any_button = dialog.get_by_role("button").first
            if any_button.count() > 0:
                try:
                    human_click(any_button, page=page, profile=profile)
                    human_delay(0.3, 0.6)
                except Exception:
                    pass
            return "dismissed_unknown"

    return "none"

def handle_popup(page, profile=None, account_label="", max_checks=3):
    for _ in range(max_checks):
        result = _check_popup_once(page, profile=profile, account_label=account_label)
        if result == "crucial_stop":
            return "crucial_stop"
        if result == "none":
            break
    return result

def human_idle_before_switch(page, profile=None):
    human_delay(1, 3)

def resilient_find(page_or_scope, strategies, description=""):
    """Tries a ranked list of locator strategies in order (most
    precise first) and returns the first one that actually finds
    something. Each strategy is a zero-arg function returning a
    Playwright locator.

    Returns (locator, strategy_index) on success, or (None, None) if
    nothing matched."""
    for i, strategy in enumerate(strategies):
        try:
            locator = strategy()
            if locator.count() > 0:
                if i > 0:
                    print(f"  [self-heal] '{description}' found via fallback #{i+1} "
                          f"-- primary selector may have changed on Zerodha's end, worth checking.")
                return locator, i
        except Exception:
            continue
    print(f"  [self-heal] Could not find '{description}' via any of {len(strategies)} strategies.")
    return None, None

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en'] });
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""

STEALTH_CONTEXT_ARGS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "locale": "en-IN",
    "timezone_id": "Asia/Kolkata",
    "viewport": {"width": 1366, "height": 768},
}