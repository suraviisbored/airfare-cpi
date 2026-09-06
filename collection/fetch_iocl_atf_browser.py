import os
import json
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

output_dir = "/Users/scrape/data/raw/benchmarks"
os.makedirs(output_dir, exist_ok=True)
timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
output_file = os.path.join(output_dir, f"iocl_atf_{timestamp_str}.json")

url = "https://iocl.com/aviation-turbine-fuel"

record = {
    "source": "IOCL_DOMESTIC_ATF",
    "url": url,
    "collected_at": datetime.now(timezone.utc).isoformat(),
    "currency": "INR/KL",
    "status": "PENDING",
    "prices": {}
}

print("=" * 60)
print("     IOCL ATF COLLECTOR (BROWSER AUTOMATION)")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Extract rows from tables on the page
        rows = page.locator("table tr").all()
        for row in rows:
            text = row.inner_text().strip()
            cols = [c.strip() for c in text.split("\t") if c.strip()]
            if not cols:
                cols = [c.strip() for c in text.split("\n") if c.strip()]
                
            if cols and any(metro in cols[0].upper() for metro in ["DELHI", "MUMBAI", "KOLKATA", "CHENNAI"]):
                record["prices"][cols[0].title()] = cols[1:]

        if record["prices"]:
            record["status"] = "SUCCESS"
        else:
            record["status"] = "NO_DATA_EXTRACTED"

    except Exception as e:
        record["status"] = "BROWSER_ERROR"
        record["error_message"] = str(e)
    finally:
        browser.close()

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(record, f, indent=2)

print(f"Status      : {record['status']}")
print(f"Prices found: {len(record['prices'])} metros")
print(f"Saved to    : {output_file}")
print("=" * 60)
