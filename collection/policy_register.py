import os
import requests
from datetime import datetime

TARGETS = [
    "google.com",
    "makemytrip.com",
    "ixigo.com",
    "cleartrip.com",
    "easemytrip.com",
    "goindigo.in",
    "airindia.com",
    "spicejet.com",
]

POLICY_DIR = "/Users/scrape/data/policy"
os.makedirs(POLICY_DIR, exist_ok=True)

def run_policy_check():
    summary_path = os.path.join(POLICY_DIR, "policy_summary.csv")
    with open(summary_path, "w", encoding="utf-8") as out:
        out.write("domain,status_code,snapshot_file\n")
        
        for domain in TARGETS:
            url = f"https://www.{domain}/robots.txt"
            snapshot_file = f"{domain}_robots.txt"
            target_file = os.path.join(POLICY_DIR, snapshot_file)
            
            try:
                res = requests.get(url, headers={"User-Agent": "SIH-Research-Bot/1.0"}, timeout=8)
                with open(target_file, "w", encoding="utf-8") as sf:
                    sf.write(res.text)
                out.write(f"{domain},{res.status_code},{snapshot_file}\n")
                print(f"[✓] Policy captured for {domain:15s} (HTTP {res.status_code})")
            except Exception as e:
                print(f"[-] Failed to fetch {domain}: {e}")
                out.write(f"{domain},FAILED,None\n")

if __name__ == "__main__":
    run_policy_check()