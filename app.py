import streamlit as st
import pandas as pd
import numpy as np
import os
import subprocess
import sys

# --- FORCE INSTALL PLOTLY ---
# This ensures Plotly is installed even if requirements.txt fails or is missing
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
    import plotly.express as px
    import plotly.graph_objects as go
# ---------------------------

from datetime import datetime, timedelta

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(
    page_title="Ad Spend Anomaly Detector",
    page_icon="🚨",
    layout="wide"
)

# --- CSS STYLING (Fixed for Visibility) ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        color: #31333F; 
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 10px;
    }
    .metric-card h4 {
        color: #31333F;
        margin-top: 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. DATA GENERATOR (SIMULATION MODE) ---
def generate_data(scenario="Normal"):
    dates = pd.date_range(end=datetime.now(), periods=24*4, freq='15T')
    
    data = {
        'timestamp': dates,
        'spend': np.random.normal(500, 50, size=len(dates)), 
        'impressions': np.random.normal(5000, 500, size=len(dates)),
        'clicks': np.random.normal(150, 20, size=len(dates)),
        'conversions': np.random.randint(0, 5, size=len(dates))
    }
    
    df = pd.DataFrame(data)
    
    # Scenario Injection Logic
    if scenario == "Rule A: Zero Conversions (Broken Pixel)":
        df.loc[df.index[-16:], 'conversions'] = 0
        df.loc[df.index[-16:], 'spend'] = 600 

    elif scenario == "Rule B: Pacing Breach (Overspend)":
        df.loc[df.index[-10:], 'spend'] = 3000 
    
    elif scenario == "Rule C: Cost Spike (High CPM)":
        df.loc[df.index[-8:], 'impressions'] = 500
        df.loc[df.index[-8:], 'spend'] = 800

    elif scenario == "Rule D: Quality Drop (Low CTR)":
        df.loc[df.index[-20:], 'clicks'] = 10 

    # Derived Metrics
    df['cpm'] = (df['spend'] / df['impressions']) * 1000
    df['ctr'] = (df['clicks'] / df['impressions']) * 100
    df['cpa'] = df['spend'] / df['conversions'].replace(0, np.nan) 
    
    return df

# --- 2. LOGIC ENGINE (SHARED) ---
def run_logic_checks(metrics):
    """
    metrics: dict containing all necessary data points
    """
    alerts = []
    
    # --- TIER 1: KILL SWITCH ---
    
    # Rule A: Zero Conversions
    # IF Spend > ₹5,000 (scaled) AND Conversions == 0 (last 4 hours)
    if metrics['spend_last_4h'] > 5000 and metrics['conv_last_4h'] == 0:
        alerts.append({
            "Tier": "Tier 1: Kill Switch",
            "Rule": "Rule A (Zero Conversions)",
            "Severity": "Critical (P0)",
            "Message": f"ZERO conversions in last 4h despite spending ₹{metrics['spend_last_4h']:,.2f}.",
            "Action": "Check Landing Page / Pixel"
        })

    # Rule B: Pacing Breach
    # IF Daily Spend > (Daily_Budget * 1.2)
    limit = metrics['daily_budget'] * 1.2
    if metrics['daily_spend'] > limit:
        alerts.append({
            "Tier": "Tier 1: Kill Switch",
            "Rule": "Rule B (Pacing Breach)",
            "Severity": "Critical (P0)",
            "Message": f"Daily spend ₹{metrics['daily_spend']:,.2f} exceeded budget limit (₹{metrics['daily_budget']}) by >20%.",
            "Action": "Pause Campaign / Check Bids"
        })

    # --- TIER 2: TREND WATCH ---
    
    # Rule C: Cost Spike (CPM)
    # IF CPM > (Average * 1.5)
    if metrics['current_cpm'] > (metrics['avg_cpm'] * 1.5):
        alerts.append({
            "Tier": "Tier 2: Trend Watch",
            "Rule": "Rule C (CPM Spike)",
            "Severity": "High (P1)",
            "Message": f"Current CPM (₹{metrics['current_cpm']:.2f}) is >50% above average (₹{metrics['avg_cpm']:.2f}).",
            "Action": "Check Auction Competition"
        })

    # Rule D: Quality Drop (CTR)
    # IF CTR < (Average * 0.5)
    if metrics['current_ctr'] < (metrics['avg_ctr'] * 0.5):
        alerts.append({
            "Tier": "Tier 2: Trend Watch",
            "Rule": "Rule D (CTR Drop)",
            "Severity": "Medium (P2)",
            "Message": f"Current CTR ({metrics['current_ctr']:.2f}%) dropped >50% below average ({metrics['avg_ctr']:.2f}%).",
            "Action": "Check Creative Fatigue"
        })

    return alerts

# --- 3. FRONTEND UI ---

st.title("🛡️ Proactive Ad Anomaly Detector")

# Create Tabs
tab1, tab2 = st.tabs(["📊 Simulation Dashboard", "🛠️ Manual Test Lab"])

# ==========================================
# TAB 1: SIMULATION DASHBOARD (Existing)
# ==========================================
with tab1:
    col_ctrl, col_main = st.columns([1, 3])
    
    with col_ctrl:
        st.subheader("Simulation Controls")
        selected_scenario = st.selectbox(
            "Inject Failure Scenario",
            [
                "Normal",
                "Rule A: Zero Conversions (Broken Pixel)",
                "Rule B: Pacing Breach (Overspend)",
                "Rule C: Cost Spike (High CPM)",
                "Rule D: Quality Drop (Low CTR)"
            ]
        )
        st.info("Select a scenario to generate synthetic data and trigger the Logic Engine.")

    with col_main:
        # Generate Data
        df = generate_data(selected_scenario)
        
        # Prepare Metrics for Logic Engine
        current_data = df.iloc[-1]
        last_4h_data = df.iloc[-16:]
        
        sim_metrics = {
            'spend_last_4h': last_4h_data['spend'].sum(),
            'conv_last_4h': last_4h_data['conversions'].sum(),
            'daily_spend': df['spend'].sum(),
            'daily_budget': 50000,
            'current_cpm': current_data['cpm'],
            'avg_cpm': df['cpm'].mean(),
            'current_ctr': current_data['ctr'],
            'avg_ctr': df['ctr'].mean()
        }

        alerts = run_logic_checks(sim_metrics)

        # Display Alerts
        if alerts:
            st.error(f"⚠️ {len(alerts)} Active Anomalies Detected")
            for alert in alerts:
                st.markdown(f"""
                <div class="metric-card">
                    <h4>{alert['Severity']} | {alert['Rule']}</h4>
                    <p><b>Diagnosis:</b> {alert['Message']}</p>
                    <p><b>Action:</b> {alert['Action']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ System Nominal. No anomalies detected.")

        # Charts
        st.divider()
        if "Zero Conversions" in selected_scenario:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['spend'], name="Spend (₹)", line=dict(color='blue')))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['conversions'], name="Conversions", yaxis='y2', line=dict(color='green')))
            fig.update_layout(yaxis2=dict(overlaying='y', side='right'), title="Spend vs Conversions (Last 24h)")
            st.plotly_chart(fig, use_container_width=True)
        elif "CPM" in selected_scenario:
            threshold = df['cpm'].mean() * 1.5
            fig = px.line(df, x='timestamp', y='cpm', title="CPM Trend vs Threshold")
            fig.add_hline(y=threshold, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
        elif "Overspend" in selected_scenario:
            df['cumulative_spend'] = df['spend'].cumsum()
            budget_limit = 50000 * 1.2
            fig = px.area(df, x='timestamp', y='cumulative_spend', title="Daily Cumulative Spend")
            fig.add_hline(y=budget_limit, line_color="red", annotation_text="Budget Kill Switch")
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = px.line(df, x='timestamp', y=['spend', 'cpm', 'ctr'], title="Campaign Health Metrics")
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 2: MANUAL TEST LAB (New)
# ==========================================
with tab2:
    st.markdown("### 🧪 Test Your Own Data")
    st.markdown("Input raw campaign metrics below to see if they trigger the anomaly detection rules.")
    
    # Input Form
    with st.form("manual_input_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 1. Tier 1: Safety Inputs")
            in_spend_4h = st.number_input("Spend (Last 4 Hours)", value=6000.0, step=100.0)
            in_conv_4h = st.number_input("Conversions (Last 4 Hours)", value=0, step=1)
            in_daily_spend = st.number_input("Total Daily Spend", value=55000.0, step=1000.0)
            in_budget = st.number_input("Daily Budget Setting", value=50000.0, step=1000.0)
            
        with col2:
            st.markdown("#### 2. Tier 2: Current Status")
            in_curr_cpm = st.number_input("Current CPM (₹)", value=250.0, step=10.0)
            in_curr_ctr = st.number_input("Current CTR (%)", value=1.5, step=0.1)
            
        with col3:
            st.markdown("#### 3. Historical Context")
            in_avg_cpm = st.number_input("Historical Avg CPM (₹)", value=100.0, help="Your account's normal CPM")
            in_avg_ctr = st.number_input("Historical Avg CTR (%)", value=2.0, help="Your account's normal CTR")
            
        submitted = st.form_submit_button("🚨 Run Anomaly Check")
        
    # Logic Processing for Manual Inputs
    if submitted:
        # Build the metrics dictionary expected by the logic engine
        manual_metrics = {
            'spend_last_4h': in_spend_4h,
            'conv_last_4h': in_conv_4h,
            'daily_spend': in_daily_spend,
            'daily_budget': in_budget,
            'current_cpm': in_curr_cpm,
            'avg_cpm': in_avg_cpm,
            'current_ctr': in_curr_ctr,
            'avg_ctr': in_avg_ctr
        }
        
        # Run Logic
        manual_alerts = run_logic_checks(manual_metrics)
        
        st.divider()
        st.subheader("Diagnosis Results")
        
        if manual_alerts:
            st.error(f"⚠️ {len(manual_alerts)} Rules Triggered!")
            for alert in manual_alerts:
                st.markdown(f"""
                <div class="metric-card">
                    <h4>{alert['Severity']} | {alert['Rule']}</h4>
                    <p><b>Trigger:</b> {alert['Message']}</p>
                    <p><b>System Action:</b> {alert['Action']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No Anomalies Detected. Data is within normal parameters.")
            st.balloons()
