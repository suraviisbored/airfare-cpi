import glob
import os
import numpy as np
import pandas as pd

# ---------------------------------------------------------
# 1. Official Weights (Derived from DGCA & CPI Standards)
# ---------------------------------------------------------
# Advance Booking Weights (gamma_w): Sum = 1.0
WINDOW_WEIGHTS = {
    1: 0.10,  # T+1  (Urgent/Last minute)
    7: 0.25,  # T+7  (Short-term planned)
    15: 0.35,  # T+15 (Standard advance booking)
    30: 0.20,  # T+30 (Early leisure/business)
    45: 0.10,  # T+45 (Long-horizon planning)
}

# Route Traffic Weights (Omega_r): Share of top metro passenger traffic (Sum = 1.0)
ROUTE_WEIGHTS = {
    ("DEL", "BOM"): 0.28,
    ("DEL", "BLR"): 0.22,
    ("BOM", "BLR"): 0.18,
    ("DEL", "CCU"): 0.14,
    ("BLR", "HYD"): 0.10,
    ("MAA", "DEL"): 0.08,
}


def load_latest_dataset(data_dir: str = "/Users/scrape") -> pd.DataFrame:
    """Finds and loads the latest scraped CSV dataset."""
    files = glob.glob(os.path.join(data_dir, "airfare_cpi_data_*.csv"))
    if not files:
        raise FileNotFoundError("No airfare CSV files found!")
    latest_file = max(files, key=os.path.getctime)
    print(f"[*] Loading dataset: {latest_file}")
    df = pd.read_csv(latest_file)

    # Basic data cleansing
    df = df[df["total_fare_inr"] > 500].copy()  # Filter anomalies/zeros
    return df


def calculate_cpi_index(df: pd.DataFrame):
    """
    Computes Jevons Elementary Aggregates, Route Composites, and National APIx.
    """
    records = []

    # Group by Route and Booking Horizon
    grouped = df.groupby(["origin", "destination", "advance_window_days"])

    for (origin, dest), route_df in df.groupby(["origin", "destination"]):
        route_key = (origin, dest)
        route_weight = ROUTE_WEIGHTS.get(route_key, 0.0)

        window_geom_means = {}

        for w, w_df in route_df.groupby("advance_window_days"):
            prices = w_df["total_fare_inr"].values

            # Elementary Jevons Index (Geometric Mean of prices)
            geom_mean = float(np.exp(np.mean(np.log(prices))))
            arith_mean = float(np.mean(prices))
            median_price = float(np.median(prices))

            window_geom_means[w] = geom_mean

            records.append(
                {
                    "route": f"{origin} → {dest}",
                    "origin": origin,
                    "destination": dest,
                    "window": f"T+{w}",
                    "window_days": w,
                    "sample_count": len(prices),
                    "min_fare": float(np.min(prices)),
                    "max_fare": float(np.max(prices)),
                    "median_fare": median_price,
                    "arithmetic_mean": arith_mean,
                    "geometric_mean": geom_mean,
                }
            )

    elementary_summary = pd.DataFrame(records)

    # ---------------------------------------------------------
    # Route-level Composite Index (Weighted across windows)
    # ---------------------------------------------------------
    route_composite = {}
    for (origin, dest), r_df in elementary_summary.groupby(
        ["origin", "destination"]
    ):
        composite_fare = 0.0
        total_weight_present = 0.0

        for _, row in r_df.iterrows():
            w = row["window_days"]
            weight = WINDOW_WEIGHTS.get(w, 0.0)
            composite_fare += row["geometric_mean"] * weight
            total_weight_present += weight

        if total_weight_present > 0:
            route_composite[(origin, dest)] = (
                composite_fare / total_weight_present
            )

    # ---------------------------------------------------------
    # National Composite Price Level (Laspeyres Passenger Weighting)
    # ---------------------------------------------------------
    national_composite_price = sum(
        route_composite[r] * ROUTE_WEIGHTS.get(r, 0.0)
        for r in route_composite
        if r in ROUTE_WEIGHTS
    )

    return elementary_summary, route_composite, national_composite_price


if __name__ == "__main__":
    df = load_latest_dataset()
    elem_df, route_comp, national_price = calculate_cpi_index(df)

    print("\n" + "=" * 60)
    print("      ELEMENTARY ROUTE-WINDOW PRICE METRICS (INR)")
    print("=" * 60)
    print(
        elem_df[
            [
                "route",
                "window",
                "sample_count",
                "median_fare",
                "geometric_mean",
            ]
        ].to_string(index=False)
    )

    print("\n" + "=" * 60)
    print("          WEIGHTED ROUTE COMPOSITE FARES (INR)")
    print("=" * 60)
    for (orig, dest), fare in route_comp.items():
        print(
            f"  • {orig} → {dest:4s} : ₹{fare:,.2f}  (Route Weight: {ROUTE_WEIGHTS.get((orig, dest), 0)*100:.1f}%)"
        )

    print("\n" + "=" * 60)
    print(f"  NATIONAL BASKET COMPOSITE AIRFARE : ₹{national_price:,.2f}")
    print("=" * 60)