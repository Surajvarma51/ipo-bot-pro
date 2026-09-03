"""
Comprehensive Verification Test Suite for Crest Terminal & AI IPO BOT PRO Backend.
Tests all endpoints, 2FA workflows, order synchronization with Excel, and bot status.
"""

import sys
import requests
import pyotp

BASE_URL = "http://localhost:4000"

def run_tests():
    print("=" * 60)
    print("  RUNNING FULL SERVER & APP VERIFICATION SUITE")
    print("=" * 60)

    # 1. Test Static Frontend Hosting
    print("\n[1] Testing GET / (Static Frontend)...")
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "<title>Crest" in r.text or "CREST" in r.text, "Index HTML missing expected title"
    print("  [PASS] Frontend HTML served successfully (Status 200, Size: %d bytes)" % len(r.text))

    # 2. Test Live IPO Refresh
    print("\n[2] Testing GET /api/ipos/refresh (Live Exchange Data)...")
    r = requests.get(f"{BASE_URL}/api/ipos/refresh")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert "ipos" in data and len(data["ipos"]) > 0, "No IPOs returned"
    print("  [PASS] %d IPOs returned (Source: %s, Fetched: %s)" % (data["count"], data["source"], data["fetchedAt"]))
    for ipo in data["ipos"][:3]:
        print(f"         - {ipo['sym']}: {ipo['name']} (Rs.{ipo['priceMin']}-{ipo['priceMax']}, Qty: {ipo['qty']})")


    # 3. Test Orders Excel Read
    print("\n[3] Testing GET /api/orders (applications_log.xlsx Sync)...")
    r = requests.get(f"{BASE_URL}/api/orders")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    orders = r.json().get("orders", [])
    print(f"  [PASS] Successfully read {len(orders)} historical orders from Excel log")

    # 4. Test Orders Excel Write
    print("\n[4] Testing POST /api/orders (Writing new order to Excel)...")
    new_order = {
        "accountLabel": "SV Primary (Zerodha)",
        "company": "TEMPSENS",
        "investorType": "Individual investor",
        "status": "pending",
        "upiId": "svcapital@okhdfcbank",
        "quantity": "40",
        "price": "358",
        "notes": "Automated verification test entry"
    }
    r = requests.post(f"{BASE_URL}/api/orders", json=new_order)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print(f"  [PASS] Order successfully appended to Excel log: {r.json()['message']}")

    # 5. Test Accounts Overview
    print("\n[5] Testing GET /api/accounts...")
    r = requests.get(f"{BASE_URL}/api/accounts")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    accounts = r.json().get("accounts", [])
    assert len(accounts) > 0, "No accounts returned"
    print(f"  [PASS] {len(accounts)} Demat accounts configured:")
    for acc in accounts:
        print(f"         - {acc['label']} ({acc['broker']}, Client ID: {acc['clientId']})")

    # 6. Test 2FA Setup, Confirm, Verify, and Disable
    print("\n[6] Testing 2FA Workflow (RFC 6238 TOTP)...")
    test_user_id = "test_user_99"
    # Setup
    r = requests.post(f"{BASE_URL}/api/2fa/setup", json={"userId": test_user_id, "accountLabel": "test@svcapital.in"})
    assert r.status_code == 200, "2FA setup failed"
    setup_data = r.json()
    secret = setup_data["secret"]
    assert "qrDataUrl" in setup_data and setup_data["qrDataUrl"].startswith("data:image/png;base64,"), "QR code missing"
    print("  [PASS] 2FA secret and QR code generated successfully")

    # Confirm with TOTP code
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    r = requests.post(f"{BASE_URL}/api/2fa/confirm", json={"userId": test_user_id, "code": valid_code})
    assert r.status_code == 200 and r.json().get("ok") is True, f"2FA confirm failed: {r.text}"
    print(f"  [PASS] 2FA confirmed with code {valid_code}")

    # Check status
    r = requests.get(f"{BASE_URL}/api/2fa/status/{test_user_id}")
    assert r.json().get("enabled") is True, "2FA should be enabled"
    print("  [PASS] 2FA status check returns enabled: True")

    # Verify invalid code
    r = requests.post(f"{BASE_URL}/api/2fa/verify", json={"userId": test_user_id, "code": "000000"})
    assert r.json().get("ok") is False, "Invalid code should fail verification"
    print("  [PASS] Incorrect 2FA code properly rejected")

    # Verify valid code
    r = requests.post(f"{BASE_URL}/api/2fa/verify", json={"userId": test_user_id, "code": totp.now()})
    assert r.json().get("ok") is True, "Valid code should pass verification"
    print("  [PASS] Valid 2FA code accepted")

    # Disable 2FA
    r = requests.post(f"{BASE_URL}/api/2fa/disable", json={"userId": test_user_id})
    assert r.json().get("ok") is True, "Disable failed"
    r = requests.get(f"{BASE_URL}/api/2fa/status/{test_user_id}")
    assert r.json().get("enabled") is False, "2FA should be disabled"
    print("  [PASS] 2FA disabled successfully")

    # 7. Test Bot Status Endpoint
    print("\n[7] Testing GET /api/bot/status...")
    r = requests.get(f"{BASE_URL}/api/bot/status")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    status_data = r.json()
    print(f"  [PASS] Bot Status Endpoint alive (is_running: {status_data['is_running']})")

    print("\n" + "=" * 60)
    print("  SUCCESS: ALL 7/7 TEST SUITES PASSED PERFECTLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
