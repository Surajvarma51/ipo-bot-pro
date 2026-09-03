"""
Integration Test Suite for Zerodha & NSE India Scrapers and Frontend API.
"""

import requests

BASE_URL = "http://localhost:4000"

def test_exchange_integration():
    print("=" * 60)
    print("  TESTING ZERODHA & NSE INDIA SCRAPER INTEGRATION")
    print("=" * 60)

    # 1. Sources Health Check
    print("\n[1] Testing GET /api/ipos/sources...")
    r = requests.get(f"{BASE_URL}/api/ipos/sources")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    sources = r.json()
    assert "zerodha" in sources and "nse" in sources, "Missing exchange sources"
    print(f"  [PASS] Zerodha Source: {sources['zerodha']['url']} ({sources['zerodha']['type']})")
    print(f"  [PASS] NSE India Source: {sources['nse']['url']} ({sources['nse']['type']})")

    # 2. Unified Refresh Feed Check
    print("\n[2] Testing GET /api/ipos/refresh...")
    r = requests.get(f"{BASE_URL}/api/ipos/refresh")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert "ipos" in data and len(data["ipos"]) > 0, "No IPOs returned"
    print(f"  [PASS] Fetched {data['count']} IPOs (Source: {data['source']})")
    for ipo in data["ipos"][:4]:
        sub = f"{ipo['subscriptionTimes']}x" if ipo.get("subscriptionTimes") else "—"
        sources_str = ", ".join(ipo.get("sources", []))
        print(f"         - [{sources_str}] {ipo['sym']}: {ipo['name']}")
        print(f"           Lot: {ipo['qty']} | Price: Rs.{ipo['priceMin']}-{ipo['priceMax']} | Sub: {sub} | Reg: {ipo.get('registrar', '—')}")

    # 3. Trigger Scrape Live Endpoint
    print("\n[3] Testing POST /api/ipos/scrape-live...")
    r = requests.post(f"{BASE_URL}/api/ipos/scrape-live")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    scrape_res = r.json()
    assert scrape_res.get("ok") is True, "Live scrape call failed"
    print(f"  [PASS] Live Scrape Message: {scrape_res['message']}")
    print(f"  [PASS] Scraped Dataset Count: {scrape_res['data']['count']}")

    print("\n" + "=" * 60)
    print("  SUCCESS: ZERODHA & NSE INDIA INTEGRATION VERIFIED!")
    print("=" * 60)

if __name__ == "__main__":
    test_exchange_integration()
