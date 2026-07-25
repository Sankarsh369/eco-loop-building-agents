import streamlit as st
import pandas as pd
import numpy as np
import os
import subprocess

# Set page configuration with a premium look
st.set_page_config(
    page_title="Eco-Loop Building Agents — Energy & Comfort Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling and premium aesthetics (Dark Mode Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .metric-card {
        background-color: #1e222b;
        border: 1px solid #2e3440;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #4c566a;
    }
    .metric-val-green {
        color: #a3be8c;
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-val-blue {
        color: #88c0d0;
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-val-red {
        color: #bf616a;
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #d8dee9;
        margin-top: 5px;
        font-weight: 600;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #8fbcbb, #88c0d0, #81a1c1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# App Title
st.markdown("<h1 class='main-title'>⚡ Eco-Loop Building Agents</h1>", unsafe_allow_html=True)
st.subheader("Closed-Loop Energy & Occupant Comfort Optimization")

# Sidebar Controls
st.sidebar.image("https://img.icons8.com/color/96/000000/green-home.png", width=80)
st.sidebar.header("🛠️ Simulation Controls")

CSV_PATH = "data/simulation_results.csv"

def run_simulation(steps):
    st.sidebar.warning("Running building simulation...")
    cmd = ["python", "src/main.py", "--steps", str(steps)]
    try:
        subprocess.run(cmd, check=True)
        st.sidebar.success("Simulation finished successfully!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Failed to run simulation: {e}")

sim_steps = st.sidebar.slider("Simulation Horizon (Steps)", min_value=12, max_value=288, value=288, step=12)

if st.sidebar.button("🔄 Run New Simulation"):
    run_simulation(sim_steps)

st.sidebar.markdown("---")
st.sidebar.info("""
**Performance Weights:**
- 🔋 **Energy Efficiency**: 25%
- 🌡️ **Occupant Comfort**: 20%
- 📉 **Peak Demand Shaving**: 15%
- 🌐 **Carbon Grid-Intensity**: 10%
""")

# Load Simulation Data
data_loaded = False
if os.path.exists(CSV_PATH):
    try:
        df = pd.read_csv(CSV_PATH)
        data_loaded = True
    except Exception as e:
        st.error(f"Error loading CSV results: {e}")
else:
    st.warning("⚠️ No simulation results found in `data/simulation_results.csv`. Running initial simulation now...")
    run_simulation(288)

if data_loaded:
    # Calculations
    total_baseline_energy = df['Baseline Energy (kWh)'].sum()
    total_ai_energy = df['AI Closed-Loop Energy (kWh)'].sum()
    energy_saved = ((total_baseline_energy - total_ai_energy) / total_baseline_energy) * 100
    
    total_baseline_carbon = df['Baseline Carbon (g)'].sum()
    total_ai_carbon = df['AI Carbon (g)'].sum()
    carbon_saved = ((total_baseline_carbon - total_ai_carbon) / total_baseline_carbon) * 100
    
    baseline_comfort_violations = ((df['Baseline PMV'] < -0.5) | (df['Baseline PMV'] > 0.5)).sum()
    ai_comfort_violations = ((df['AI PMV'] < -0.5) | (df['AI PMV'] > 0.5)).sum()
    
    # 4 metrics layout
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val-green">{energy_saved:.2f}%</div>
            <div class="metric-label">Net Energy Savings</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val-blue">{carbon_saved:.2f}%</div>
            <div class="metric-label">Carbon Footprint Reduction</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val-green">{(100 * (1 - ai_comfort_violations/len(df))):.1f}%</div>
            <div class="metric-label">AI Comfort Compliance</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val-red">{ai_comfort_violations} Steps</div>
            <div class="metric-label">AI Comfort Violations (vs {baseline_comfort_violations} baseline)</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Energy & Carbon", "🌡️ Thermal Comfort", "📋 Raw Results"])

    with tab1:
        st.subheader("⚡ Energy Consumption & Carbon Over Time")
        
        # Cumulative Energy
        df['Baseline Cumulative Energy (kWh)'] = df['Baseline Energy (kWh)'].cumsum()
        df['AI Cumulative Energy (kWh)'] = df['AI Closed-Loop Energy (kWh)'].cumsum()
        
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.markdown("#### Cumulative Energy Usage (kWh)")
            st.line_chart(df.set_index('Timestamp')[['Baseline Cumulative Energy (kWh)', 'AI Cumulative Energy (kWh)']])
        
        with chart_col2:
            st.markdown("#### Carbon Emissions Intensity & Savings (g)")
            st.line_chart(df.set_index('Timestamp')[['Baseline Carbon (g)', 'AI Carbon (g)']])
            
        # Grid carbon intensity reference
        st.markdown("#### Grid Carbon Intensity (gCO2/kWh)")
        st.area_chart(df.set_index('Timestamp')['Carbon Intensity (gCO2/kWh)'])

    with tab2:
        st.subheader("🌡️ Occupant Thermal Comfort Profile (PMV)")
        st.markdown("""
        **Predicted Mean Vote (PMV)** is the standard comfort index. The comfort band is **[-0.5, 0.5]**. 
        Values outside this indicate occupant thermal discomfort.
        """)
        
        # Comfort index chart
        comfort_df = df.set_index('Timestamp')[['Baseline PMV', 'AI PMV']].copy()
        comfort_df['Comfort Upper Bound'] = 0.5
        comfort_df['Comfort Lower Bound'] = -0.5
        st.line_chart(comfort_df)
        
        # Zone Temperature chart
        st.subheader("🏫 Zone Temperature vs Outdoor Conditions")
        st.line_chart(df.set_index('Timestamp')[['Baseline Temp (°C)', 'AI Closed-Loop Temp (°C)']])

    with tab3:
        st.subheader("Detailed Time-series Log")
        st.dataframe(df, use_container_width=True)
