import os
import json
import time
import uuid
import random
from datetime import datetime, timedelta
from fast_flights import FlightQuery, Passengers, create_query, get_flights

# 1. Non-negotiable 6 routes from the problem statement
ROUTES = [
    ("DEL", "BOM"),
    ("DEL", "BLR"),
    ("BOM", "BLR"),
    ("DEL", "CCU"),
    ("BLR", "HYD"),
    ("MAA", "DEL"),
]

# 2. Advance booking windows
WINDOWS = [1, 7, 15, 30, 45]

DATA_DIR = "/Users/scrape/data/raw"
os.makedirs(DATA_DIR, exist_ok=True)

def run_collector():
    today = datetime.today()
    batch_id = today.strftime("%Y%m%d_%H%M%S")
    quotes_file = os.path.join(DATA_DIR, f"quotes_{batch_id}.jsonl")
    attempts_file = os.path.join(DATA_DIR, f"attempts_{batch_id}.jsonl")
    
    total_quotes_collected = 0
    successful_cells = 0
    
    print(f"[*] Starting Production Run | Batch: {batch_id}")
    print(f"[*] Iterating across {len(ROUTES)} routes and {len(WINDOWS)} windows (Total: 30 cells)...")

    for origin, dest in ROUTES:
        for w in WINDOWS:
            target_date = (today + timedelta(days=w)).strftime("%Y-%m-%d")
            print(f"\n[*] Cell {origin}->{dest} (T+{w} | {target_date})...")
            
            attempt_record = {
                "attempt_id": str(uuid.uuid4()),
                "attempt_timestamp": datetime.utcnow().isoformat(),
                "origin": origin,
                "destination": dest,
                "advance_window_days": w,
                "target_date": target_date,
                "source": "GOOGLE_FLIGHTS",
                "quotes_count": 0,
                "outcome_code": "PENDING",
                "error_message": None
            }
            
            try:
                query = create_query(
                    flights=[FlightQuery(date=target_date, from_airport=origin, to_airport=dest)],
                    trip="one-way",
                    seat="economy",
                    passengers=Passengers(adults=1),
                )
                
                result = get_flights(query)
                flight_items = list(result)
                
                if not flight_items:
                    attempt_record["outcome_code"] = "NO_OFFERS_RETURNED"
                    write_jsonl(attempts_file, attempt_record)
                    print(f"    [-] Outcome: NO_OFFERS_RETURNED")
                    continue
                
                cell_count = 0
                for flight in flight_items:
                    raw_price = getattr(flight, "price", 0)
                    if isinstance(raw_price, str):
                        clean_price = float("".join(c for c in raw_price if c.isdigit() or c == ".") or 0)
                    else:
                        clean_price = float(raw_price or 0)
                        
                    if clean_price <= 0:
                        continue
                        
                    airlines = getattr(flight, "airlines", [])
                    airline_name = airlines[0] if airlines else getattr(flight, "name", "Unknown")
                    
                    quote = {
                        "quote_id": str(uuid.uuid4()),
                        "source": "GOOGLE_FLIGHTS",
                        "origin": origin,
                        "destination": dest,
                        "departure_date": target_date,
                        "advance_window_days": w,
                        "airline": str(airline_name),
                        "departure_time": str(getattr(flight, "departure", "N/A")),
                        "arrival_time": str(getattr(flight, "arrival", "N/A")),
                        "duration": str(getattr(flight, "duration", "N/A")),
                        "is_direct": getattr(flight, "stops", 0) == 0,
                        "total_fare_inr": clean_price,
                        "collected_at": datetime.utcnow().isoformat()
                    }
                    write_jsonl(quotes_file, quote)
                    cell_count += 1
                
                attempt_record["quotes_count"] = cell_count
                attempt_record["outcome_code"] = "SUCCESS"
                total_quotes_collected += cell_count
                successful_cells += 1
                write_jsonl(attempts_file, attempt_record)
                print(f"    [+] Saved {cell_count} flight quotes.")
                
            except Exception as e:
                print(f"    [!] Error: {e}")
                attempt_record["outcome_code"] = "TIMEOUT_OR_ERROR"
                attempt_record["error_message"] = str(e)
                write_jsonl(attempts_file, attempt_record)
                
            # Random pause between requests to prevent network throttling
            time.sleep(random.uniform(2.5, 4.0))

    print("\n" + "=" * 50)
    print(f"[✓] Batch Completed Successfully")
    print(f"    Cells Succeeded : {successful_cells} / 30")
    print(f"    Total Quotes    : {total_quotes_collected}")
    print(f"    Quotes File     : {quotes_file}")
    print(f"    Attempts File   : {attempts_file}")
    print("=" * 50)

def write_jsonl(file_path: str, record: dict):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

if __name__ == "__main__":
    run_collector()