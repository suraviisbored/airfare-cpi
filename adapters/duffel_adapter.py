import os
import uuid
from datetime import datetime


class DuffelCollectorAdapter:
    """Modular source adapter for the Duffel Flights API.

    Converts Duffel offer requests into the APIx Standard Quote Schema.
    """

    def __init__(self, api_token: str = None):
        self.token = api_token or os.getenv("DUFFEL_ACCESS_TOKEN", "")
        self.source_name = "DUFFEL_API"
        self.version = "v2.0"
        self.client = None

        if self.token:
            try:
                from duffel_api import Duffel

                self.client = Duffel(access_token=self.token)
            except ImportError:
                pass

    def search_cell(
        self, origin: str, destination: str, target_date: str, advance_days: int
    ):
        """Executes an observation search for a single route-window cell.

        Enforces: One-way, 1 adult, economy, direct/nonstop, INR.
        """
        attempt_id = str(uuid.uuid4())
        collected_at = datetime.utcnow().isoformat()

        attempt_log = {
            "attempt_id": attempt_id,
            "source": self.source_name,
            "source_adapter_version": self.version,
            "origin": origin,
            "destination": destination,
            "advance_window": f"T+{advance_days}",
            "advance_days": advance_days,
            "departure_date": target_date,
            "collected_at": collected_at,
            "outcome_code": "PENDING",
            "n_offers_returned": 0,
            "error_message": None,
        }

        # Graceful handling if token is not yet provisioned in this environment
        if not self.client:
            attempt_log["outcome_code"] = "CONFIG_ERROR"
            attempt_log["error_message"] = (
                "DUFFEL_ACCESS_TOKEN not configured or provided."
            )
            return attempt_log, []

        try:
            offer_request = (
                self.client.offer_requests.create()
                .passengers([{"type": "adult"}])
                .slices([
                    {
                        "origin": origin,
                        "destination": destination,
                        "departure_date": target_date,
                    }
                ])
                .cabin_class("economy")
                .max_connections(0)
                .return_offers()
                .execute()
            )

            raw_offers = offer_request.offers or []
            if not raw_offers:
                attempt_log["outcome_code"] = "NO_OFFERS_RETURNED"
                return attempt_log, []

            normalized_quotes = []
            for offer in raw_offers:
                if (
                    offer.total_currency != "INR"
                    or float(offer.total_amount) <= 0
                ):
                    continue

                first_slice = offer.slices[0] if offer.slices else None
                first_seg = (
                    first_slice.segments[0]
                    if (first_slice and first_slice.segments)
                    else None
                )

                carrier_name = offer.owner.name if offer.owner else "Unknown"
                flight_no = (
                    f"{first_seg.operating_carrier.iata_code}{first_seg.operating_carrier_flight_number}"
                    if first_seg
                    else "N/A"
                )

                quote = {
                    "quote_id": f"duffel_{offer.id}",
                    "attempt_id": attempt_id,
                    "source": self.source_name,
                    "origin": origin,
                    "destination": destination,
                    "departure_date": target_date,
                    "advance_window": f"T+{advance_days}",
                    "advance_days": advance_days,
                    "airline": carrier_name,
                    "flight_number": flight_no,
                    "departure_time": (
                        first_seg.departing_at if first_seg else "N/A"
                    ),
                    "arrival_time": (
                        first_seg.arriving_at if first_seg else "N/A"
                    ),
                    "is_direct": True,
                    "total_fare_inr": float(offer.total_amount),
                    "currency": "INR",
                    "collected_at": collected_at,
                }
                normalized_quotes.append(quote)

            attempt_log["n_offers_returned"] = len(normalized_quotes)
            attempt_log["outcome_code"] = (
                "SUCCESS" if normalized_quotes else "FILTERED_OUT"
            )
            return attempt_log, normalized_quotes

        except Exception as e:
            attempt_log["outcome_code"] = "API_ERROR"
            attempt_log["error_message"] = str(e)
            return attempt_log, []