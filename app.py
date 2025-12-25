import streamlit as st
import pandas as pd
import numpy as np
import os
import subprocess
import sys

# --- FORCE INSTALL PLOTLY ---
# This ensures Plotly is installed even if requirements.txt fails
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    # Use subprocess to pip install strictly within the running environment
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
    import plotly.express as px
    import plotly.graph_objects as go
# ---------------------------

from datetime import datetime, timedelta

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(
    page_title="Ad Spend Anomaly Detector",
# ... (rest of the code remains the same)
    page_icon="🚨",
    layout="wide"
)

# --- CSS STYLING ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6; /* Keep the light gray background */
        color: #31333F; /* Change text color to dark grey for readability */
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
    }
    /* Ensure the headers inside the card are also dark */
    .metric-card h4 {
        color: #31333F;
        margin-top: 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. DATA GENERATOR (SIMULATION MODE) [cite: 79] ---
# Generates realistic ad data streams with injectable anomalies
def generate_data(scenario="Normal"):
    # Base timestamps for the last 24 hours (15-min intervals)
    dates = pd.date_range(end=datetime.now(), periods=24*4, freq='15T')
    
    # Base "Normal" Data
    data = {
        'timestamp': dates,
        'spend': np.random.normal(500, 50, size=len(dates)), # Avg ₹500 per 15 mins
        'impressions': np.random.normal(5000, 500, size=len(dates)),
        'clicks': np.random.normal(150, 20, size=len(dates)),
        'conversions': np.random.randint(0, 5, size=len(dates))
    }
    
    df = pd.DataFrame(data)
    
    # Scenario Injection Logic 
    if scenario == "Rule A: Zero Conversions (Broken Pixel)":
        # Kill conversions for the last 4 hours (last 16 intervals)
        df.loc[df.index[-16:], 'conversions'] = 0
        # Ensure spend remains high to trigger alert (Waste)
        df.loc[df.index[-16:], 'spend'] = 600 

    elif scenario == "Rule B: Pacing Breach (Overspend)":
        # Massive spend spike in last few hours
        df.loc[df.index[-10:], 'spend'] = 3000 
    
    elif scenario == "Rule C: Cost Spike (High CPM)":
        # Impressions drop but spend stays same = High CPM
        df.loc[df.index[-8:], 'impressions'] = 500
        df.loc[df.index[-8:], 'spend'] = 800

    elif scenario == "Rule D: Quality Drop (Low CTR)":
        # Clicks drop significantly
        df.loc[df.index[-20:], 'clicks'] = 10 

    # Derived Metrics
    df['cpm'] = (df['spend'] / df['impressions']) * 1000
    df['ctr'] = (df['clicks'] / df['impressions']) * 100
    df['cpa'] = df['spend'] / df['conversions'].replace(0, np.nan) # Avoid div/0
    
    return df

# --- 2. LOGIC ENGINE (TIER 1 & 2) [cite: 17, 20, 28] ---
def check_anomalies(df, daily_budget=50000):
    alerts = []
    
    # Get latest data (simulating "Now")
    current_data = df.iloc[-1]
    last_4h_data = df.iloc[-16:] # Last 4 hours (16 * 15mins)
    
    # --- TIER 1: KILL SWITCH [cite: 20] ---
    
    # Rule A: Zero Conversions 
    # IF Spend > ₹8,000 (scaled for demo) AND Conversions == 0 (last 4 hours)
    recent_spend = last_4h_data['spend'].sum()
    recent_conv = last_4h_data['conversions'].sum()
    
    if recent_spend > 5000 and recent_conv == 0: # Threshold lowered for demo
        alerts.append({
            "Tier": "Tier 1: Kill Switch",
            "Rule": "Rule A (Zero Conversions)",
            "Severity": "Critical (P0)",
            "Message": f"ZERO conversions in last 4h despite spending ₹{recent_spend:,.2f}. Possible broken pixel.",
            "Action": "Check Landing Page / Pixel"
        })

    # Rule B: Pacing Breach [cite: 25]
    # IF Daily Spend > (Daily_Budget * 1.2)
    daily_spend = df['spend'].sum() # Simplified for demo (treating total df as daily)
    if daily_spend > (daily_budget * 1.2):
        alerts.append({
            "Tier": "Tier 1: Kill Switch",
            "Rule": "Rule B (Pacing Breach)",
            "Severity": "Critical (P0)",
            "Message": f"Daily spend ₹{daily_spend:,.2f} exceeded budget limit (₹{daily_budget}) by >20%.",
            "Action": "Pause Campaign / Check Bids"
        })

    # --- TIER 2: TREND WATCH [cite: 28] ---
    
    # Rule C: Cost Spike (CPM) [cite: 31]
    # IF CPM > (Average * 1.5)
    avg_cpm = df['cpm'].mean()
    current_cpm = current_data['cpm']
    
    if current_cpm > (avg_cpm * 1.5):
        alerts.append({
            "Tier": "Tier 2: Trend Watch",
            "Rule": "Rule C (CPM Spike)",
            "Severity": "High (P1)",
            "Message": f"Current CPM (₹{current_cpm:.2f}) is >50% above average (₹{avg_cpm:.2f}).",
            "Action": "Check Auction Competition"
        })

    # Rule D: Quality Drop (CTR) [cite: 33]
    # IF CTR < (Average * 0.5)
    avg_ctr = df['ctr'].mean()
    current_ctr = current_data['ctr']
    
    if current_ctr < (avg_ctr * 0.5):
        alerts.append({
            "Tier": "Tier 2: Trend Watch",
            "Rule": "Rule D (CTR Drop)",
            "Severity": "Medium (P2)",
            "Message": f"Current CTR ({current_ctr:.2f}%) dropped >50% below average ({avg_ctr:.2f}%).",
            "Action": "Check Creative Fatigue"
        })

    return alerts

# --- 3. FRONTEND UI [cite: 40] ---

# Sidebar for Controls
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1055/1055644.png", width=50)
st.sidebar.title("Anomaly Settings")

# Scenario Selector 
selected_scenario = st.sidebar.selectbox(
    "Inject Failure Scenario",
    [
        "Normal",
        "Rule A: Zero Conversions (Broken Pixel)",
        "Rule B: Pacing Breach (Overspend)",
        "Rule C: Cost Spike (High CPM)",
        "Rule D: Quality Drop (Low CTR)"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("This prototype simulates the logic engine described in 'Proactive Anomaly Detection for Ad Spend'.")

# Main Dashboard
st.title("🛡️ Proactive Ad Anomaly Detector")
st.markdown("### The Pulse Dashboard ")

# 1. Generate & Process Data
df = generate_data(selected_scenario)
alerts = check_anomalies(df)

# 2. Display Status & Alerts
col1, col2 = st.columns([2, 1])

with col1:
    if alerts:
        st.error(f"⚠️ {len(alerts)} Active Anomalies Detected")
        for alert in alerts:
            with st.container():
                st.markdown(f"""
                <div class="metric-card">
                    <h4>{alert['Severity']} | {alert['Rule']}</h4>
                    <p><b>Diagnosis:</b> {alert['Message']}</p>
                    <p><b>Recommended Action:</b> {alert['Action']}</p>
                </div>
                <br>
                """, unsafe_allow_html=True)
    else:
        st.success("✅ System Nominal. No anomalies detected.")
        st.caption("Monitoring 500+ campaigns across Google & Meta APIs.")

with col2:
    st.markdown("#### Live Metrics (Last 15m)")
    last_row = df.iloc[-1]
    st.metric("Spend", f"₹{last_row['spend']:.2f}", delta_color="inverse")
    st.metric("CPM", f"₹{last_row['cpm']:.2f}", delta=f"{last_row['cpm'] - df['cpm'].mean():.2f}")
    st.metric("CTR", f"{last_row['ctr']:.2f}%")

# 3. Visual Analysis [cite: 86]
st.divider()
st.subheader("📉 Visual Evidence")

# Dynamic Charting based on Scenario
if "Zero Conversions" in selected_scenario:
    st.caption("Visualizing Rule A: High Spend vs Zero Conversions")
    
    # Dual Axis Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['spend'], name="Spend (₹)", line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['conversions'], name="Conversions", yaxis='y2', line=dict(color='green')))
    
    fig.update_layout(
        yaxis=dict(title="Spend"),
        yaxis2=dict(title="Conversions", overlaying='y', side='right'),
        title="Spend vs Conversions (Last 24h)"
    )
    st.plotly_chart(fig, use_container_width=True)

elif "CPM" in selected_scenario:
    st.caption("Visualizing Rule C: CPM Cost Spike")
    threshold = df['cpm'].mean() * 1.5
    
    fig = px.line(df, x='timestamp', y='cpm', title="CPM Trend vs Threshold")
    fig.add_hline(y=threshold, line_dash="dash", line_color="red", annotation_text="Anomaly Threshold")
    st.plotly_chart(fig, use_container_width=True)

elif "Overspend" in selected_scenario:
    st.caption("Visualizing Rule B: Cumulative Spend vs Budget")
    df['cumulative_spend'] = df['spend'].cumsum()
    budget_limit = 50000 * 1.2
    
    fig = px.area(df, x='timestamp', y='cumulative_spend', title="Daily Cumulative Spend")
    fig.add_hline(y=budget_limit, line_color="red", annotation_text="Budget Kill Switch")
    st.plotly_chart(fig, use_container_width=True)

else:
    # Default View
    st.caption("General Performance Overview")
    fig = px.line(df, x='timestamp', y=['spend', 'cpm', 'ctr'], title="Campaign Health Metrics")
    st.plotly_chart(fig, use_container_width=True)

# 4. Raw Data View
with st.expander("View Raw Data Log"):
    st.dataframe(df.sort_values(by='timestamp', ascending=False).head(10))
