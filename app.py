from datetime import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="National Airfare Price Index (APIx) Dashboard",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Real-time Airfare Price Index (APIx) for CPI")
st.markdown(
    "**Smart India Hackathon** | High-Frequency High-Dimensional Inflation Tracking Engine"
)

# Load data
from calculate_cpi import (
    ROUTE_WEIGHTS,
    WINDOW_WEIGHTS,
    calculate_cpi_index,
    load_latest_dataset,
)

try:
    df = load_latest_dataset()
    elem_df, route_comp, national_price = calculate_cpi_index(df)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Top KPI Summary Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="National Composite Airfare", value=f"₹{national_price:,.2f}"
    )
with kpi2:
    st.metric(
        label="Baseline APIx Index",
        value="100.00",
        help="Indexed relative to initial crawl benchmark",
    )
with kpi3:
    st.metric(label="Monitored Metro Routes", value=f"{len(route_comp)}")
with kpi4:
    st.metric(label="Total Raw Flight Observations", value=f"{len(df):,}")

st.divider()

# Layout: Visualizations
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📈 Advance-Booking Price Escalation Curve")
    st.caption("How ticket prices surge from T+45 days down to T+1 day")

    fig_curve = px.line(
        elem_df,
        x="window_days",
        y="geometric_mean",
        color="route",
        markers=True,
        labels={
            "window_days": "Advance Booking Horizon (Days)",
            "geometric_mean": "Jevons Geometric Mean Fare (₹)",
        },
    )
    fig_curve.update_xaxes(autorange="reversed")  # 45 -> 1 day
    st.plotly_chart(fig_curve, use_container_width=True)

with col_right:
    st.subheader("🏢 Route-Level Price Comparison")
    st.caption("Weighted route fares vs route passenger share")

    route_summary_df = pd.DataFrame(
        [
            {
                "Route": f"{k[0]}→{k[1]}",
                "Weighted Fare (₹)": v,
                "Traffic Share": f"{ROUTE_WEIGHTS.get(k, 0)*100:.1f}%",
            }
            for k, v in route_comp.items()
        ]
    )

    fig_bar = px.bar(
        route_summary_df,
        x="Route",
        y="Weighted Fare (₹)",
        color="Route",
        text_auto=".2s",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Granular Table View
st.subheader("📋 Granular Elementary Price Relatives")
st.dataframe(
    elem_df[
        [
            "route",
            "window",
            "sample_count",
            "min_fare",
            "median_fare",
            "arithmetic_mean",
            "geometric_mean",
        ]
    ].style.format(
        {
            "min_fare": "₹{:.0f}",
            "median_fare": "₹{:.0f}",
            "arithmetic_mean": "₹{:.2f}",
            "geometric_mean": "₹{:.2f}",
        }
    ),
    use_container_width=True,
)