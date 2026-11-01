
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time

# =====================================================
# CONFIG
# =====================================================

import os

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:10001"
).rstrip("/")
import os


st.set_page_config(
    page_title="Smart Transport System - Abeokuta",
    layout="wide"
)

st.title("🎓 Smart IoT Transport System (Abeokuta Case Study)")

# =====================================================
# SAFE API FUNCTIONS
# =====================================================

def get_latest():
    try:
        res = requests.get(f"{API_URL}/latest", timeout=5)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        st.error(f"Unable to connect to transport API: {e}")
        return []
    except ValueError:
        st.error("The API returned invalid JSON data.")
        return []

def get_metrics():
    try:
        res = requests.get(f"{API_URL}/metrics", timeout=5)
        res.raise_for_status()
        return res.json()
    except requests.RequestException:
        return {}
    except ValueError:
        return {}

# =====================================================
# LOAD DATA
# =====================================================

latest_data = get_latest()
metrics = get_metrics()

df = pd.DataFrame(latest_data)

# =====================================================
# KPI SECTION
# =====================================================

st.subheader("📊 System Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Active Buses", len(df))
col2.metric("Avg Speed (km/h)", round(metrics.get("avg_speed") or 0, 2))
col3.metric("Avg Occupancy", round(metrics.get("avg_occupancy") or 0, 2))
col4.metric("Congested Buses", metrics.get("congested_buses", 0))

st.divider()

# =====================================================
# MAP SECTION
# =====================================================

st.subheader("🗺️ Live Bus Tracking Map")

if not df.empty and {"lat", "lon"}.issubset(df.columns):

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    map_df = df.dropna(subset=["lat", "lon"])

    if not map_df.empty:

        fig = px.scatter_map(
            map_df,
            lat="lat",
            lon="lon",
            hover_name="bus_id",
            hover_data=["stop_id", "speed_kmh", "occupancy"],
            color="speed_kmh",
            size="occupancy",
            zoom=10,
            height=600,
            map_style="open-street-map"
        )

        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0)
        )

        fig.update_traces(marker=dict(opacity=0.75))

        st.plotly_chart(fig, width="stretch")

    else:
        st.warning("Bus location coordinates are not available.")

else:
    st.warning("No live data yet. Start your MQTT publisher and main.py.")

# =====================================================
# TABLE VIEW
# =====================================================

st.subheader("📍 Live Fleet Data")

if not df.empty:
    st.dataframe(df, width="stretch")
else:
    st.info("No fleet telemetry records available yet.")

# =====================================================
# SYSTEM HEALTH
# =====================================================

st.subheader("🧠 System Intelligence Metrics")

st.json(metrics)

# =====================================================
# AUTO REFRESH
# =====================================================

time.sleep(3)
st.rerun()
time.sleep(3)
st.rerun()