import time
from datetime import datetime, timedelta
from fast_flights import FlightQuery, Passengers, create_query, get_flights

def run_preflight():
    print("[*] Running Day 1 Preflight Check on DEL -> BOM...")
    target_date = (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    query = create_query(
        flights=[FlightQuery(date=target_date, from_airport="DEL", to_airport="BOM")],
        trip="one-way",
        seat="economy",
        passengers=Passengers(adults=1),
    )
    
    result = get_flights(query)
    carriers = set()
    total_quotes = 0
    
    for flight in result:
        airlines = getattr(flight, "airlines", [])
        name = airlines[0] if airlines else getattr(flight, "name", "Unknown")
        if name:
            carriers.add(str(name))
            total_quotes += 1
            
    print("\n" + "=" * 50)
    print("           PREFLIGHT RESULTS REPORT")
    print("=" * 50)
    print(f"Target Route        : DEL -> BOM (T+7: {target_date})")
    print(f"Total Quotes Found  : {total_quotes}")
    print(f"Distinct Carriers   : {len(carriers)}")
    print(f"Airlines Captured   : {sorted(list(carriers))}")
    print("=" * 50)

if __name__ == "__main__":
    run_preflight()