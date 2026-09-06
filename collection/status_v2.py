import os
import sys
import glob
import json
from collections import Counter

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
att_files = sorted(glob.glob(os.path.join(RAW_DIR, "attempts_*.jsonl")))
quo_files = sorted(glob.glob(os.path.join(RAW_DIR, "quotes_*.jsonl")))

print("=" * 75)
print("             APIx AIRFARE COLLECTION AUDIT DASHBOARD")
print("=" * 75)

attempts = []
for f in att_files:
    with open(f, "r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                attempts.append(json.loads(line))

quotes = []
for f in quo_files:
    with open(f, "r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                quotes.append(json.loads(line))

print(f"Total Ingestion Runs Processed : {len(att_files)}")
print(f"Total Scheduled Search Attempts: {len(attempts)}")
print(f"Total Real Quotes Retained     : {len(quotes)}")

if not attempts:
    print("No data logged yet.")
    sys.exit(0)

# Outcome Breakdown
outcomes = Counter(a.get("outcome_code", "UNKNOWN") for a in attempts)
print("\n--- ATTEMPT OUTCOME CODE METRICS ---")
for code, count in outcomes.items():
    pct = (count / len(attempts)) * 100
    print(f"  {code:<22} : {count:>5} ({pct:>5.1f}%)")

# Currency & Quality Sanity Checks
currencies = Counter(q.get("currency") for q in quotes)
airlines = Counter(q.get("airline") for q in quotes)
na_duration = sum(1 for q in quotes if q.get("duration") == "N/A")
na_departure = sum(1 for q in quotes if q.get("departure_time") == "N/A")

print("\n--- DATA INTEGRITY & SANITY CHECKS ---")
print(f"  Currencies Recorded         : {dict(currencies)}")
print(f"  Airlines Captured           : {dict(airlines)}")
print(f"  Missing (N/A) Durations     : {na_duration} (Target: 0)")
print(f"  Missing (N/A) Departure Tm : {na_departure} (Target: 0)")

# 12-Route Cell Observation Matrix
routes = ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10", "R11", "R12"]
print("\n--- 12-ROUTE CELL OBSERVATION MATRIX ---")
print(f"{'Route':<6} | {'Attempts':<10} | {'Success':<10} | {'Quotes':<10} | {'Category'}")
print("-" * 55)
for r in routes:
    r_att = [a for a in attempts if a.get("route_id") == r]
    r_succ = [a for a in r_att if a.get("outcome_code") == "SUCCESS"]
    r_quo = [q for q in quotes if q.get("route_id") == r]
    category = "Core" if int(r[1:]) <= 8 else "Supplementary"
    print(f"{r:<6} | {len(r_att):<10} | {len(r_succ):<10} | {len(r_quo):<10} | {category}")

print("=" * 75)