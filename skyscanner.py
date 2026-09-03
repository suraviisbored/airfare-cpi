import time
from datetime import datetime, timedelta
import pandas as pd
from fast_flights import FlightQuery, Passengers, create_query, get_flights

# 1. SIH Representative Routes
routes = [
    ("DEL", "BOM"),
    ("DEL", "BLR"),
    ("BOM", "BLR"),
    ("DEL", "CCU"),
    ("BLR", "HYD"),
    ("MAA", "DEL"),
]

# 2. Advance booking horizons (T+1, T+7, T+15, T+30, T+45)
windows = [1, 7, 15, 30, 45]
today = datetime.today()

records = []

# Crawl all routes and booking horizons
for origin, dest in routes:
    for w in windows:
        flight_date = (today + timedelta(days=w)).strftime("%Y-%m-%d")
        print(f"[*] Fetching {origin} -> {dest} for {flight_date} (T+{w})...")

        try:
            query = create_query(
                flights=[
                    FlightQuery(
                        date=flight_date,
                        from_airport=origin,
                        to_airport=dest,
                    )
                ],
                trip="one-way",
                seat="economy",
                passengers=Passengers(adults=1),
            )

            # Retrieve results
            result = get_flights(query)

            count = 0
            for flight in result:
                # Handle price parsing
                raw_price = getattr(flight, "price", 0)
                if isinstance(raw_price, str):
                    clean_price = float(
                        "".join(c for c in raw_price if c.isdigit() or c == ".")
                        or 0
                    )
                else:
                    clean_price = float(raw_price or 0)

                # Extract airline names
                airlines = getattr(flight, "airlines", [])
                airline_name = (
                    airlines[0]
                    if airlines
                    else getattr(flight, "name", "Unknown")
                )

                records.append(
                    {
                        "scrape_timestamp": datetime.now().isoformat(),
                        "origin": origin,
                        "destination": dest,
                        "advance_window_days": w,
                        "flight_date": flight_date,
                        "airline": str(airline_name),
                        "departure_time": str(
                            getattr(flight, "departure", "N/A")
                        ),
                        "arrival_time": str(getattr(flight, "arrival", "N/A")),
                        "duration": str(getattr(flight, "duration", "N/A")),
                        "is_direct": getattr(flight, "stops", 0) == 0,
                        "total_fare_inr": clean_price,
                    }
                )
                count += 1

            print(f"[+] Found {count} flights.")
            time.sleep(2)  # Delay between requests to avoid rate limits

        except Exception as e:
            print(f"[-] Error on {origin}->{dest} ({flight_date}): {e}")

# Save collected data to CSV
if records:
    df = pd.DataFrame(records)
    out_file = f"airfare_cpi_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df.to_csv(out_file, index=False)
    print(f"\n[✓] Successfully collected {len(df)} records into '{out_file}'")
else:
    print("\n[-] No records captured.")