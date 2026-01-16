"""Streamlit dashboard for SSI monitoring."""

import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DATA_PROCESSED_DIR
from src.metrics import (
    calculate_category_metrics,
    calculate_overall_metrics,
    calculate_temporal_metrics,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="SSI Monitoring Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("🏥 Surgical Site Infection (SSI) Monitoring Dashboard")
st.markdown("---")

# Load data
@st.cache_data
def load_data():
    """Load processed data."""
    csv_path = DATA_PROCESSED_DIR / "ssi_processed.csv"
    if not csv_path.exists():
        st.error(f"Processed data not found at {csv_path}. Please run the pipeline first: `python -m src.pipeline`")
        st.stop()
    return pd.read_csv(csv_path)

try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")

# Date range filter
if "surgery_date" in df.columns:
    df["surgery_date"] = pd.to_datetime(df["surgery_date"])
    min_date = df["surgery_date"].min().date()
    max_date = df["surgery_date"].max().date()
    
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    
    if len(date_range) == 2:
        df = df[
            (df["surgery_date"].dt.date >= date_range[0])
            & (df["surgery_date"].dt.date <= date_range[1])
        ]
    elif len(date_range) == 1:
        df = df[df["surgery_date"].dt.date >= date_range[0]]

# Category filter
if "procedure_category" in df.columns:
    categories = ["All"] + sorted(df["procedure_category"].unique().tolist())
    selected_category = st.sidebar.selectbox("Procedure Category", categories)
    if selected_category != "All":
        df = df[df["procedure_category"] == selected_category]

# Specialty filter (if available)
if "Specialty" in df.columns:
    specialties = ["All"] + sorted(df["Specialty"].dropna().unique().tolist())
    selected_specialty = st.sidebar.selectbox("Specialty", specialties)
    if selected_specialty != "All":
        df = df[df["Specialty"] == selected_specialty]

# Main dashboard
# KPI Tiles
st.header("Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

overall_metrics = calculate_overall_metrics(df)
temporal_monthly = calculate_temporal_metrics(df, period="month")

with col1:
    st.metric(
        "Overall SSI Rate",
        f"{overall_metrics['overall_ssi_rate']:.4f}",
        f"{overall_metrics['overall_ssi_rate']*100:.2f}%",
    )

with col2:
    if len(temporal_monthly) > 0:
        last_month_rate = temporal_monthly.iloc[-1]["ssi_rate"]
        st.metric(
            "Last Month Rate",
            f"{last_month_rate:.4f}",
            f"{last_month_rate*100:.2f}%",
        )
    else:
        st.metric("Last Month Rate", "N/A")

with col3:
    if len(temporal_monthly) > 0 and "rolling_3m_rate" in temporal_monthly.columns:
        rolling_3m = temporal_monthly["rolling_3m_rate"].iloc[-1]
        st.metric(
            "Rolling 3-Month Rate",
            f"{rolling_3m:.4f}",
            f"{rolling_3m*100:.2f}%",
        )
    else:
        st.metric("Rolling 3-Month Rate", "N/A")

with col4:
    st.metric(
        "Total Surgeries",
        f"{overall_metrics['total_procedures']:,}",
        f"{overall_metrics['total_infections']} infections",
    )

st.markdown("---")

# Trend Chart
st.header("SSI Rate Trend (Monthly)")
if len(temporal_monthly) > 0:
    fig_trend = go.Figure()
    
    fig_trend.add_trace(
        go.Scatter(
            x=temporal_monthly["month"],
            y=temporal_monthly["ssi_rate"],
            mode="lines+markers",
            name="SSI Rate",
            line=dict(color="steelblue", width=2),
            marker=dict(size=8),
        )
    )
    
    if "rolling_3m_rate" in temporal_monthly.columns:
        fig_trend.add_trace(
            go.Scatter(
                x=temporal_monthly["month"],
                y=temporal_monthly["rolling_3m_rate"],
                mode="lines",
                name="3-Month Rolling Avg",
                line=dict(color="orange", width=2, dash="dash"),
            )
        )
    
    overall_rate = temporal_monthly["ssi_rate"].mean()
    fig_trend.add_hline(
        y=overall_rate,
        line_dash="dot",
        line_color="gray",
        annotation_text=f"Overall Avg: {overall_rate:.4f}",
    )
    
    fig_trend.update_layout(
        height=400,
        hovermode="x unified",
        xaxis_title="Month",
        yaxis_title="SSI Rate",
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("Insufficient data for trend chart")

# Category Analysis
st.header("SSI Rate by Procedure Category")
category_metrics = calculate_category_metrics(df, min_volume=30)

if len(category_metrics) > 0:
    # Bar chart
    top_n = st.slider("Number of categories to display", 5, 20, 10)
    top_categories = category_metrics.head(top_n).sort_values("ssi_rate", ascending=True)
    
    fig_category = go.Figure()
    fig_category.add_trace(
        go.Bar(
            x=top_categories["ssi_rate"],
            y=top_categories["procedure_category"],
            orientation="h",
            marker_color="steelblue",
            error_x=dict(
                type="data",
                array=top_categories["ci_upper"] - top_categories["ssi_rate"],
                arrayminus=top_categories["ssi_rate"] - top_categories["ci_lower"],
            ),
        )
    )
    
    overall_rate = category_metrics["ssi_rate"].mean()
    fig_category.add_vline(
        x=overall_rate,
        line_dash="dot",
        line_color="red",
        annotation_text=f"Overall: {overall_rate:.4f}",
    )
    
    fig_category.update_layout(
        height=max(400, top_n * 30),
        xaxis_title="SSI Rate",
        yaxis_title="Procedure Category",
    )
    
    st.plotly_chart(fig_category, use_container_width=True)
    
    # Data table
    with st.expander("View full category metrics table"):
        st.dataframe(
            category_metrics[["procedure_category", "total_procedures", "infections", "ssi_rate", "ci_lower", "ci_upper"]].style.format({
                "ssi_rate": "{:.4f}",
                "ci_lower": "{:.4f}",
                "ci_upper": "{:.4f}",
            })
        )
else:
    st.info("No categories meet minimum volume threshold (30 procedures)")

# Volume vs Rate Scatter
st.header("Procedure Volume vs SSI Rate")
if len(category_metrics) > 0:
    fig_scatter = go.Figure()
    
    fig_scatter.add_trace(
        go.Scatter(
            x=category_metrics["total_procedures"],
            y=category_metrics["ssi_rate"],
            mode="markers",
            marker=dict(
                size=category_metrics["infections"],
                sizemode="area",
                sizeref=category_metrics["infections"].max() / 100,
                color=category_metrics["ssi_rate"],
                colorscale="Reds",
                showscale=True,
                colorbar=dict(title="SSI Rate"),
            ),
            text=category_metrics["procedure_category"],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Volume: %{x}<br>"
                "SSI Rate: %{y:.4f}<br>"
                "Infections: %{marker.size}<extra></extra>"
            ),
        )
    )
    
    fig_scatter.update_layout(
        height=500,
        xaxis_title="Total Procedures (Volume)",
        yaxis_title="SSI Rate",
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)
else:
    st.info("Insufficient data for scatter plot")

# Footer
st.markdown("---")
st.markdown(
    "<small>SSI Monitoring Dashboard | Data updated automatically from pipeline</small>",
    unsafe_allow_html=True,
)
