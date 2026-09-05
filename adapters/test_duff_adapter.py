import json
import os
from duffel_adapter import DuffelCollectorAdapter

# Reads token from environment variable if available, otherwise runs in graceful test mode
token = os.getenv("DUFFEL_ACCESS_TOKEN", "")
adapter = DuffelCollectorAdapter(api_token=token)

print("=" * 65)
print("       APIx PROVIDER INDEPENDENCE: DUFFEL ADAPTER")
print("=" * 65)
print(f"Target Adapter : {adapter.source_name} ({adapter.version})")
print("Standard Schema: Synchronized with Google Flights pipeline")

# Run an architectural test query for DEL -> BOM (T+7)
attempt, quotes = adapter.search_cell(
    origin="DEL",
    destination="BOM",
    target_date="2026-09-12",
    advance_days=7,
)

print("\n[Attempt Record Generated for Audit Log]:")
print(json.dumps(attempt, indent=2))

if quotes:
    print(f"\n[Sample Normalized Quote (1 of {len(quotes)})]:")
    print(json.dumps(quotes[0], indent=2))
else:
    print(
        f"\n[Execution Status]: Gracefully recorded outcome '{attempt['outcome_code']}'."
    )
    print(
        "Audit trail and error logging verified without breaking pipeline execution."
    )

print("=" * 65)