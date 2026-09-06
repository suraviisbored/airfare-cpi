import os
import json
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

output_dir = "/Users/scrape/data/raw/benchmarks"
os.makedirs(output_dir, exist_ok=True)
timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
output_file = os.path.join(output_dir, f"iocl_atf_{timestamp_str}.json")

# IOCL canonical ATF URL
url = "https://iocl.com/aviation-turbine-fuel"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://iocl.com/",
})

print("=" * 60)
print("       IOCL AVIATION TURBINE FUEL (ATF) COLLECTOR")
print("=" * 60)

record = {
    "source": "IOCL_DOMESTIC_ATF",
    "url": url,
    "collected_at": datetime.now(timezone.utc).isoformat(),
    "currency": "INR/KL",
    "status": "PENDING",
    "prices": {}
}

try:
    # Explicitly allow following redirects (handles 301, 302, 307)
    response = session.get(url, allow_redirects=True, timeout=15)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        tables = soup.find_all("table")
        parsed = False

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if cols and any(metro in cols[0].upper() for metro in ["DELHI", "MUMBAI", "KOLKATA", "CHENNAI"]):
                    metro_name = cols[0].title()
                    # Retain applicable rate columns
                    record["prices"][metro_name] = cols[1:]
                    parsed = True

        if parsed:
            record["status"] = "SUCCESS"
        else:
            record["status"] = "TABLE_STRUCTURE_CHANGED"
    else:
        record["status"] = f"HTTP_{response.status_code}"

except Exception as e:
    record["status"] = "FETCH_ERROR"
    record["error_message"] = str(e)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(record, f, indent=2)

print(f"Final Status: {record['status']}")
print(f"Output File : {output_file}")
print("=" * 60)
