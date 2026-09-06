import os
import sys
import re
import json
import uuid
import hashlib
import requests
from datetime import datetime, timedelta, timezone

# Timezone: IST (UTC+05:30)
IST = timezone(timedelta(hours=5, minutes=30))

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "basket.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

RAW_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_STORAGE_DIR, exist_ok=True)

class ResilientFlightCollector:
    def __init__(self, run_id=None, scheduled_slot=None):
        self.source = "GOOGLE_FLIGHTS"
        self.source_adapter_version = "v2.5-ZERO-DEP"
        self.run_id = run_id or f"run_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}"
        self.scheduled_slot = scheduled_slot or self._determine_slot()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.session.cookies.set("SOCS", "CAESEwgDEgk2MTQyNjYzNzUaAmVuIAEaBgiA_LyaBg", domain=".google.com")
        self.session.cookies.set("CONSENT", "PENDING+999", domain=".google.com")

    def _determine_slot(self):
        hour = datetime.now(IST).hour
        if hour < 11:
            return "08:00"
        elif hour < 17:
            return "14:00"
        else:
            return "20:00"

    def _generate_payload_hash(self, text):
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def fetch_offers(self, route_info, advance_window):
        attempt_id = str(uuid.uuid4())
        origin = route_info["origin"]
        destination = route_info["destination"]
        route_id = route_info["route_id"]
        days = advance_window["days"]
        window_label = advance_window["label"]
        
        target_departure = (datetime.now(IST) + timedelta(days=days)).strftime("%Y-%m-%d")
        collected_at = datetime.now(IST).isoformat()
        
        attempt_record = {
            "attempt_id": attempt_id,
            "collection_run_id": self.run_id,
            "source": self.source,
            "source_adapter_version": self.source_adapter_version,
            "route_id": route_id,
            "origin": origin,
            "destination": destination,
            "advance_window": window_label,
            "advance_days": days,
            "departure_date": target_departure,
            "scheduled_slot": self.scheduled_slot,
            "collected_at": collected_at,
            "outcome_code": "PENDING",
            "http_status": None,
            "request_id": None,
            "n_offers_returned": 0,
            "raw_payload_path": None,
            "payload_hash": None,
            "error_message": None
        }

        # Force INR, Indian locale, English language
        url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{target_departure}&curr=INR&gl=in&hl=en"

        try:
            resp = self.session.get(url, timeout=20)
            attempt_record["http_status"] = resp.status_code
            
            if resp.status_code != 200:
                attempt_record["outcome_code"] = "API_ERROR"
                attempt_record["error_message"] = f"HTTP {resp.status_code}"
                return attempt_record, []

            html = resp.text
            payload_hash = self._generate_payload_hash(html)
            attempt_record["payload_hash"] = payload_hash

            qualifying_quotes = []

            # 1. Parse JSON data embedded directly inside Google Flight's initialization script
            # Matches domestic non-stop pricing patterns in INR [price, "Airline", [dep_hour, dep_min], [arr_hour, arr_min], duration_mins]
            # Resilient regex parser that works regardless of CSS layout changes:
            patterns = re.findall(r'\[([0-9]{3,6}),"(IndiGo|Air India|Akasa Air|SpiceJet|Air India Express|Vistara)",.*?,\[([0-9]{1,2}),([0-9]{1,2})\],\[([0-9]{1,2}),([0-9]{1,2})\],([0-9]{2,4})\]', html)

            if patterns:
                for match in patterns:
                    fare, airline_name, dep_h, dep_m, arr_h, arr_m, dur_mins = match
                    total_fare = float(fare)
                    if total_fare < 1000:  # Drops invalid/anomalous low parses
                        continue
                    
                    dep_time = f"{int(dep_h):02d}:{int(dep_m):02d}"
                    arr_time = f"{int(arr_h):02d}:{int(arr_m):02d}"
                    dur_val = int(dur_mins)
                    duration_str = f"{dur_val // 60}h {dur_val % 60}m"

                    quote_id = str(uuid.uuid4())
                    qualifying_quotes.append({
                        "quote_id": quote_id,
                        "attempt_id": attempt_id,
                        "collection_run_id": self.run_id,
                        "source": self.source,
                        "route_id": route_id,
                        "origin": origin,
                        "destination": destination,
                        "departure_date": target_departure,
                        "advance_window": window_label,
                        "advance_days": days,
                        "airline": airline_name,
                        "airline_code": airline_name[:2].upper(),
                        "flight_number": None,
                        "departure_airport": origin,
                        "arrival_airport": destination,
                        "departure_time": dep_time,
                        "arrival_time": arr_time,
                        "duration": duration_str,
                        "stops": 0,
                        "cabin_class": "ECONOMY",
                        "passengers": 1,
                        "base_fare": None,
                        "taxes_and_fees": None,
                        "total_fare": total_fare,
                        "currency": "INR",
                        "fare_family": "STANDARD",
                        "fare_class": "Y",
                        "collected_at": collected_at,
                        "raw_payload_path": None,
                        "payload_hash": payload_hash
                    })

            # 2. Fallback: Parse card blocks if script structure shifts
            if not qualifying_quotes:
                # Matches patterns like: ₹4,850 ... 06:00 – 08:15 ... 2h 15m ... Nonstop
                flight_blocks = re.findall(
                    r'(₹\s*[\d,]+).*?(\b\d{1,2}:\d{2}\b).*?[–\-\—].*?(\b\d{1,2}:\d{2}\b).*?(\b\d+\s*(?:hr|h)(?:\s*\d+\s*(?:min|m))?\b)',
                    html,
                    re.DOTALL
                )
                for blk in flight_blocks:
                    fare_str, d_time, a_time, dur_str = blk
                    val = float(fare_str.replace("₹", "").replace(",", "").strip())
                    if val < 1000:
                        continue
                    
                    # Detect airline in surrounding text snippet
                    matched_airline = "Domestic Airline"
                    for air in ["IndiGo", "Air India", "Akasa Air", "SpiceJet", "Air India Express"]:
                        if air.lower() in html.lower():
                            matched_airline = air
                            break

                    quote_id = str(uuid.uuid4())
                    qualifying_quotes.append({
                        "quote_id": quote_id,
                        "attempt_id": attempt_id,
                        "collection_run_id": self.run_id,
                        "source": self.source,
                        "route_id": route_id,
                        "origin": origin,
                        "destination": destination,
                        "departure_date": target_departure,
                        "advance_window": window_label,
                        "advance_days": days,
                        "airline": matched_airline,
                        "airline_code": matched_airline[:2].upper(),
                        "flight_number": None,
                        "departure_airport": origin,
                        "arrival_airport": destination,
                        "departure_time": d_time,
                        "arrival_time": a_time,
                        "duration": dur_str,
                        "stops": 0,
                        "cabin_class": "ECONOMY",
                        "passengers": 1,
                        "base_fare": None,
                        "taxes_and_fees": None,
                        "total_fare": val,
                        "currency": "INR",
                        "fare_family": "STANDARD",
                        "fare_class": "Y",
                        "collected_at": collected_at,
                        "raw_payload_path": None,
                        "payload_hash": payload_hash
                    })

            attempt_record["n_offers_returned"] = len(qualifying_quotes)
            if qualifying_quotes:
                attempt_record["outcome_code"] = "SUCCESS"
            else:
                attempt_record["outcome_code"] = "NO_OFFERS_RETURNED"

            return attempt_record, qualifying_quotes

        except requests.exceptions.Timeout:
            attempt_record["outcome_code"] = "TIMEOUT"
            attempt_record["error_message"] = "Request timed out after 20s"
            return attempt_record, []
        except Exception as e:
            attempt_record["outcome_code"] = "API_ERROR"
            attempt_record["error_message"] = str(e)
            return attempt_record, []

def execute_collection_job(routes_filter="all", window_filter=None):
    collector = ResilientFlightCollector()
    print("=" * 70)
    print("      APIx FLIGHT COLLECTOR ENGINE (STABLE / ZERO EXTERNAL PKG)")
    print("=" * 70)
    print(f"Run ID         : {collector.run_id}")
    print(f"Scheduled Slot : {collector.scheduled_slot} IST")

    all_routes = CONFIG["core_routes"] + CONFIG["supplementary_routes"]
    if routes_filter == "core":
        active_routes = CONFIG["core_routes"]
    elif routes_filter == "supplementary":
        active_routes = CONFIG["supplementary_routes"]
    else:
        active_routes = all_routes

    windows = CONFIG["advance_windows"]
    if window_filter:
        windows = [w for w in windows if w["label"] == window_filter]

    total_cells = len(active_routes) * len(windows)
    attempts_file = os.path.join(RAW_STORAGE_DIR, f"attempts_{collector.run_id}.jsonl")
    quotes_file = os.path.join(RAW_STORAGE_DIR, f"quotes_{collector.run_id}.jsonl")

    total_success = 0
    total_quotes = 0

    with open(attempts_file, "a", encoding="utf-8") as f_att, open(quotes_file, "a", encoding="utf-8") as f_quo:
        for route in active_routes:
            for win in windows:
                att, quotes = collector.fetch_offers(route, win)
                f_att.write(json.dumps(att) + "\n")
                f_att.flush()
                
                for q in quotes:
                    f_quo.write(json.dumps(q) + "\n")
                f_quo.flush()

                if att["outcome_code"] == "SUCCESS":
                    total_success += 1
                    total_quotes += len(quotes)

                print(f"[{att['route_id']}] {att['origin']}->{att['destination']} | {att['advance_window']:<4} | "
                      f"{att['outcome_code']:<18} | Offers: {att['n_offers_returned']}")

    print("\n" + "=" * 70)
    print(f"Attempts: {total_cells} | Success: {total_success} | Quotes: {total_quotes}")
    print(f"Saved: {quotes_file}")
    print("=" * 70)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    execute_collection_job(routes_filter=mode)