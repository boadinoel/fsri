import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Argentis FSRI-Lite Pro",
    page_icon="🌾",
    layout="wide"
)

st.title("🌾 Argentis FSRI-Lite Pro")
st.markdown("**Food-System Risk Index** - Real-time agricultural risk monitoring")

# API base URL (adjust for deployment)
API_BASE = "http://localhost:8000"

# Sidebar controls
st.sidebar.header("Risk Parameters")
crop = st.sidebar.selectbox("Crop", ["corn", "srw_wheat"])
state = st.sidebar.selectbox("State", ["IL", "IA", "IN", "OH", "NE", "KS", "MO", "MN"])
export_flag = st.sidebar.checkbox("Export Restrictions Active")
county_fips = st.sidebar.text_input("County FIPS (optional)", placeholder="17043")

# Fetch FSRI data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_fsri_data(crop, state, export_flag, county_fips):
    try:
        params = {
            "crop": crop,
            "state": state,
            "export_flag": export_flag
        }
        if county_fips:
            params["county_fips"] = county_fips
            
        response = requests.get(f"{API_BASE}/fsri", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"API connection error: {e}")
        return None

# Get data
data = fetch_fsri_data(crop, state, export_flag, county_fips)

if data:
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "FSRI Score", 
            f"{data['fsri']}/100",
            help="Composite Food-System Risk Index"
        )
    
    with col2:
        confidence_color = {
            "High": "🟢", 
            "Medium": "🟡", 
            "Low": "🔴"
        }
        st.metric(
            "Confidence", 
            f"{confidence_color.get(data['confidence'], '⚪')} {data['confidence']}"
        )
    
    with col3:
        st.metric(
            "Movement Event (7d)", 
            f"{data['movement_event_7d']['p']:.0%}",
            help=data['movement_event_7d']['reason']
        )
    
    with col4:
        st.metric(
            "Last Updated",
            datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')).strftime("%H:%M UTC")
        )

    # Risk breakdown
    st.subheader("Risk Component Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Subscore chart
        subscores = data['subScores']
        df_scores = pd.DataFrame([
            {"Component": "Production", "Score": subscores['production'], "Weight": "40%"},
            {"Component": "Movement", "Score": subscores['movement'], "Weight": "35%"},
            {"Component": "Biosecurity", "Score": subscores['biosecurity'], "Weight": "20%"},
            {"Component": "Policy", "Score": subscores['policy'], "Weight": "5%"}
        ])
        
        fig = px.bar(
            df_scores, 
            x="Component", 
            y="Score",
            color="Score",
            color_continuous_scale="RdYlGn_r",
            title="Risk Component Scores",
            range_y=[0, 100]
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Horizons chart
        horizons = data['horizons']
        df_horizons = pd.DataFrame([
            {"Days": 0, "FSRI": data['fsri']},
            {"Days": 5, "FSRI": horizons['d5']},
            {"Days": 15, "FSRI": horizons['d15']},
            {"Days": 30, "FSRI": horizons['d30']}
        ])
        
        fig2 = px.line(
            df_horizons,
            x="Days",
            y="FSRI",
            title="Risk Forecast Horizons",
            markers=True,
            range_y=[0, 100]
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)

    # Risk drivers
    st.subheader("Key Risk Drivers")
    for i, driver in enumerate(data['drivers'], 1):
        st.write(f"**{i}.** {driver}")

    # Raw data (expandable)
    with st.expander("Raw API Response"):
        st.json(data)

else:
    st.error("Unable to fetch FSRI data. Check API connection.")
    
    # Show sample data structure
    st.subheader("Expected Data Structure")
    sample_data = {
        "fsri": 45.2,
        "subScores": {
            "production": 38.5,
            "movement": 52.1,
            "policy": 0.0,
            "biosecurity": 35.8
        },
        "drivers": [
            "Elevated waterway transport risk",
            "Normal production conditions",
            "No recent HPAI outbreaks detected"
        ],
        "confidence": "Medium",
        "horizons": {"d5": 44.8, "d15": 43.2, "d30": 41.5}
    }
    st.json(sample_data)

# Footer
st.markdown("---")
st.markdown("*Argentis FSRI-Lite Pro v0.1 - Physical risk assessment for agricultural commodities*")
