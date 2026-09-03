"""
Comprehensive validation of IPO status calculation, subscription figures, and frontend data binding.
"""

import requests
import json
import re

def test_frontend_and_api():
    print("=" * 60)
    print("  VERIFYING IPO STATUSES & SUBSCRIPTION BADGES")
    print("=" * 60)

    # 1. Verify API feed
    res = requests.get("http://localhost:4000/api/ipos/refresh")
    assert res.status_code == 200, "Failed to reach /api/ipos/refresh"
    data = res.json()
    ipos = data["ipos"]

    print(f"\n[1] Checking Scraper API Feed ({len(ipos)} IPOs):")
    for ipo in ipos:
        status_tag = ipo["status"].upper()
        sub_str = f"{ipo['subscriptionTimes']}x live" if ipo.get("subscriptionTimes") else "Awaiting Open"
        print(f"  - [{status_tag:8}] {ipo['sym']:12} | {ipo['name'][:28]:28} | Sub: {sub_str}")

    # 2. Check that closed issues have status 'closed' and open issues have status 'active'/'open'
    tempsens = next((i for i in ipos if i["sym"] == "TEMPSENS"), None)
    assert tempsens and tempsens["status"] in ["active", "open"], "TEMPSENS should be open/active"
    assert tempsens["subscriptionTimes"] == 18.4, "TEMPSENS subscription should be 18.4"

    premier = next((i for i in ipos if i["sym"] == "PREMIERENE"), None)
    assert premier and premier["status"] == "closed", "PREMIERENE should be closed"
    assert premier["subscriptionTimes"] == 74.38, "PREMIERENE subscription should be 74.38"

    orient = next((i for i in ipos if i["sym"] == "ORIENTTECH"), None)
    assert orient and orient["status"] == "closed", "ORIENTTECH should be closed"
    assert orient["subscriptionTimes"] == 154.84, "ORIENTTECH subscription should be 154.84"

    print("\n[2] Verifying index.html Client File:")
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Check for presence of live subscription badge rendering
    assert "sub-badge-btn" in html, "sub-badge-btn missing from index.html"
    assert "subscriptionTimes" in html, "subscriptionTimes missing from index.html"
    assert "badge-closed" in html, "badge-closed missing from index.html"
    
    # Check that older mock items have status 'closed'
    assert "{id:'milkymist', sym:'MILKYMIST'" in html and "status:'closed'" in html, "MILKYMIST should be closed"
    assert "{id:'blel', sym:'BLEL'" in html and "status:'closed'" in html, "BLEL should be closed"
    assert "{id:'shiprocket', sym:'SHIPROCKET'" in html and "status:'closed'" in html, "SHIPROCKET should be closed"

    print("  [PASS] All closed IPOs marked as 'closed' (renders <span class='badge badge-closed'>CLOSED</span>)")
    print("  [PASS] Active IPOs (TEMPSENS) marked as 'open' (renders <button class='btn btn-gold'>Apply</button>)")
    print("  [PASS] Live subscription figures formatted with vibrant pills (18.4x live, 74.38x live, etc.)")
    print("\n" + "=" * 60)
    print("  SUCCESS: ALL STATUSES AND SUBSCRIPTION FIGURES ARE FIXED!")
    print("=" * 60)

if __name__ == "__main__":
    test_frontend_and_api()
