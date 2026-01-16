"""Streamlit dashboard for SSI monitoring."""

import logging
from pathlib import Path

import numpy as np
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

def format_value(value, format_type="float", decimals=4):
    """Format value, replacing NaN with 'Not available'."""
    if pd.isna(value) or (isinstance(value, (float, np.floating)) and (np.isnan(value) or np.isinf(value))):
        return "Not available"
    if format_type == "float":
        try:
            return f"{float(value):.{decimals}f}"
        except (ValueError, TypeError):
            return "Not available"
    elif format_type == "percent":
        try:
            return f"{float(value)*100:.2f}%"
        except (ValueError, TypeError):
            return "Not available"
    elif format_type == "integer":
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return "Not available"
    else:
        return str(value) if value is not None else "Not available"

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
    # Replace NaN values in string columns with "Not available" for display
    string_cols = df.select_dtypes(include=['object']).columns
    for col in string_cols:
        df[col] = df[col].fillna("Not available")
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")

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
    overall_rate = overall_metrics['overall_ssi_rate']
    st.metric(
        "Overall SSI Rate",
        format_value(overall_rate, "float", 4),
        format_value(overall_rate, "percent") if not pd.isna(overall_rate) else "Not available",
    )

with col2:
    if len(temporal_monthly) > 0:
        last_month_rate = temporal_monthly.iloc[-1]["ssi_rate"]
        st.metric(
            "Last Month Rate",
            format_value(last_month_rate, "float", 4),
            format_value(last_month_rate, "percent") if not pd.isna(last_month_rate) else "Not available",
        )
    else:
        st.metric("Last Month Rate", "Not available")

with col3:
    if len(temporal_monthly) > 0 and "rolling_3m_rate" in temporal_monthly.columns:
        rolling_3m = temporal_monthly["rolling_3m_rate"].iloc[-1]
        st.metric(
            "Rolling 3-Month Rate",
            format_value(rolling_3m, "float", 4),
            format_value(rolling_3m, "percent") if not pd.isna(rolling_3m) else "Not available",
        )
    else:
        st.metric("Rolling 3-Month Rate", "Not available")

with col4:
    st.metric(
        "Total Surgeries",
        format_value(overall_metrics['total_procedures'], "integer"),
        f"{format_value(overall_metrics['total_infections'], 'integer')} infections",
    )

st.markdown("---")

# Trend Chart
st.header("📈 SSI Rate Trend (Monthly)")
st.caption("**Description**: Shows the monthly SSI rate over time with a rolling 3-month average. The gray dashed line indicates the overall average rate. Use this to identify trends, spikes, or patterns in infection rates.")
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
    if not pd.isna(overall_rate):
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
st.header("📊 SSI Rate by Procedure Category")
st.caption("**Description**: Displays the top procedure categories ranked by SSI rate. Error bars show 95% confidence intervals. The red dashed line indicates the overall average. Categories with rates significantly above the average may require targeted interventions.")
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
    if not pd.isna(overall_rate):
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
        # Replace NaN with "Not available" in the dataframe
        display_df = category_metrics[["procedure_category", "total_procedures", "infections", "ssi_rate", "ci_lower", "ci_upper"]].copy()
        display_df = display_df.fillna("Not available")
        st.dataframe(
            display_df.style.format({
                "ssi_rate": lambda x: format_value(x, "float", 4) if isinstance(x, (int, float)) and not pd.isna(x) else "Not available",
                "ci_lower": lambda x: format_value(x, "float", 4) if isinstance(x, (int, float)) and not pd.isna(x) else "Not available",
                "ci_upper": lambda x: format_value(x, "float", 4) if isinstance(x, (int, float)) and not pd.isna(x) else "Not available",
                "total_procedures": lambda x: format_value(x, "integer") if isinstance(x, (int, float)) and not pd.isna(x) else "Not available",
                "infections": lambda x: format_value(x, "integer") if isinstance(x, (int, float)) and not pd.isna(x) else "Not available",
            }, na_rep="Not available")
        )
else:
    st.info("No categories meet minimum volume threshold (30 procedures)")

# Volume vs Rate Scatter
st.header("🎯 Procedure Volume vs SSI Rate")
st.caption("**Description**: Bubble chart showing the relationship between procedure volume and SSI rate. Bubble size represents the number of infections. Categories in the upper-right quadrant (high volume + high rate) are priority targets for quality improvement initiatives.")
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

st.markdown("---")

# Additional Visualizations Section
st.header("📉 Additional Analytics")

# Create two columns for layout
col_left, col_right = st.columns(2)

with col_left:
    # SSI Rate Distribution
    st.subheader("📊 SSI Rate Distribution")
    st.caption("**Description**: Histogram showing the distribution of SSI rates across all procedure categories. Helps identify if most categories cluster around a specific rate or if there are outliers.")
    
    if len(category_metrics) > 0:
        fig_dist = go.Figure()
        fig_dist.add_trace(
            go.Histogram(
                x=category_metrics["ssi_rate"],
                nbinsx=20,
                marker_color="steelblue",
                marker_line_color="white",
                marker_line_width=1,
            )
        )
        
        # Add mean line
        mean_rate = category_metrics["ssi_rate"].mean()
        if not pd.isna(mean_rate):
            fig_dist.add_vline(
                x=mean_rate,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Mean: {mean_rate:.4f}",
            )
        
        fig_dist.update_layout(
            height=350,
            xaxis_title="SSI Rate",
            yaxis_title="Number of Categories",
            showlegend=False,
        )
        
        st.plotly_chart(fig_dist, use_container_width=True)
    else:
        st.info("Insufficient data for distribution chart")

    # Top vs Bottom Performers
    st.subheader("🏆 Top vs Bottom Performers")
    st.caption("**Description**: Comparison of the best and worst performing categories. Top performers have the lowest SSI rates, while bottom performers have the highest. This helps identify best practices and areas needing improvement.")
    
    if len(category_metrics) >= 6:
        # Get top 5 and bottom 5
        top_5 = category_metrics.tail(5).sort_values("ssi_rate", ascending=True)
        bottom_5 = category_metrics.head(5).sort_values("ssi_rate", ascending=False)
        
        fig_comparison = go.Figure()
        
        # Top performers (lowest rates)
        fig_comparison.add_trace(
            go.Bar(
                x=top_5["procedure_category"],
                y=top_5["ssi_rate"],
                name="Top 5 (Lowest Rates)",
                marker_color="green",
                text=top_5["ssi_rate"].round(4),
                textposition="outside",
            )
        )
        
        # Bottom performers (highest rates)
        fig_comparison.add_trace(
            go.Bar(
                x=bottom_5["procedure_category"],
                y=bottom_5["ssi_rate"],
                name="Bottom 5 (Highest Rates)",
                marker_color="red",
                text=bottom_5["ssi_rate"].round(4),
                textposition="outside",
            )
        )
        
        fig_comparison.update_layout(
            height=400,
            xaxis_title="Procedure Category",
            yaxis_title="SSI Rate",
            barmode="group",
            xaxis_tickangle=-45,
        )
        
        st.plotly_chart(fig_comparison, use_container_width=True)
    else:
        st.info("Need at least 6 categories for comparison")

with col_right:
    # Infection Count Distribution
    st.subheader("🔢 Infection Count Distribution")
    st.caption("**Description**: Shows how many infections each category has. Categories with high infection counts, even if rates are moderate, contribute significantly to the total infection burden and should be prioritized.")
    
    if len(category_metrics) > 0:
        # Sort by infection count
        top_infections = category_metrics.nlargest(15, "infections")
        
        fig_infections = go.Figure()
        fig_infections.add_trace(
            go.Bar(
                x=top_infections["procedure_category"],
                y=top_infections["infections"],
                marker_color="crimson",
                text=top_infections["infections"],
                textposition="outside",
            )
        )
        
        fig_infections.update_layout(
            height=350,
            xaxis_title="Procedure Category",
            yaxis_title="Number of Infections",
            xaxis_tickangle=-45,
            showlegend=False,
        )
        
        st.plotly_chart(fig_infections, use_container_width=True)
    else:
        st.info("Insufficient data for infection count chart")

    # Risk Matrix
    st.subheader("⚠️ Risk Matrix")
    st.caption("**Description**: Categorizes procedures into risk quadrants based on volume and SSI rate. High-risk categories (high volume + high rate) require immediate attention, while low-risk categories (low volume + low rate) represent best practices.")
    
    if len(category_metrics) > 0:
        # Calculate medians for quadrants
        median_volume = category_metrics["total_procedures"].median()
        median_rate = category_metrics["ssi_rate"].median()
        
        # Handle NaN in medians
        if pd.isna(median_volume):
            median_volume = 0
        if pd.isna(median_rate):
            median_rate = 0
        
        # Categorize
        category_metrics["risk_category"] = category_metrics.apply(
            lambda row: "High Risk" if (row["total_procedures"] > median_volume and row["ssi_rate"] > median_rate)
            else "High Volume, Low Rate" if (row["total_procedures"] > median_volume and row["ssi_rate"] <= median_rate)
            else "Low Volume, High Rate" if (row["total_procedures"] <= median_volume and row["ssi_rate"] > median_rate)
            else "Low Risk",
            axis=1
        )
        
        # Color mapping
        color_map = {
            "High Risk": "red",
            "High Volume, Low Rate": "orange",
            "Low Volume, High Rate": "yellow",
            "Low Risk": "green"
        }
        
        fig_risk = go.Figure()
        
        for risk_type in ["High Risk", "High Volume, Low Rate", "Low Volume, High Rate", "Low Risk"]:
            risk_data = category_metrics[category_metrics["risk_category"] == risk_type]
            if len(risk_data) > 0:
                fig_risk.add_trace(
                    go.Scatter(
                        x=risk_data["total_procedures"],
                        y=risk_data["ssi_rate"],
                        mode="markers+text",
                        name=risk_type,
                        marker=dict(
                            size=risk_data["infections"],
                            sizemode="area",
                            sizeref=category_metrics["infections"].max() / 50,
                            color=color_map[risk_type],
                            opacity=0.7,
                        ),
                        text=risk_data["procedure_category"],
                        textposition="top center",
                        hovertemplate=(
                            "<b>%{text}</b><br>"
                            "Volume: %{x}<br>"
                            "SSI Rate: %{y:.4f}<br>"
                            "Risk: " + risk_type + "<extra></extra>"
                        ),
                    )
                )
        
        # Add quadrant lines
        if not pd.isna(median_rate) and median_rate > 0:
            fig_risk.add_hline(
                y=median_rate,
                line_dash="dash",
                line_color="gray",
                annotation_text=f"Median Rate: {median_rate:.4f}",
            )
        if not pd.isna(median_volume) and median_volume > 0:
            fig_risk.add_vline(
                x=median_volume,
                line_dash="dash",
                line_color="gray",
                annotation_text=f"Median Volume: {median_volume:.0f}",
            )
        
        fig_risk.update_layout(
            height=400,
            xaxis_title="Total Procedures (Volume)",
            yaxis_title="SSI Rate",
            hovermode="closest",
        )
        
        st.plotly_chart(fig_risk, use_container_width=True)
    else:
        st.info("Insufficient data for risk matrix")

st.markdown("---")

# Summary Statistics Table
st.header("📋 Summary Statistics")
st.caption("**Description**: Key statistical measures for SSI rates across all procedure categories. Provides a quick overview of central tendencies, spread, and distribution characteristics.")

if len(category_metrics) > 0:
    summary_stats = {
        "Metric": [
            "Mean SSI Rate",
            "Median SSI Rate",
            "Standard Deviation",
            "Minimum SSI Rate",
            "Maximum SSI Rate",
            "25th Percentile",
            "75th Percentile",
            "Total Categories",
            "Total Procedures",
            "Total Infections",
        ],
        "Value": [
            format_value(category_metrics['ssi_rate'].mean(), "float", 4),
            format_value(category_metrics['ssi_rate'].median(), "float", 4),
            format_value(category_metrics['ssi_rate'].std(), "float", 4),
            format_value(category_metrics['ssi_rate'].min(), "float", 4),
            format_value(category_metrics['ssi_rate'].max(), "float", 4),
            format_value(category_metrics['ssi_rate'].quantile(0.25), "float", 4),
            format_value(category_metrics['ssi_rate'].quantile(0.75), "float", 4),
            format_value(len(category_metrics), "integer"),
            format_value(category_metrics['total_procedures'].sum(), "integer"),
            format_value(category_metrics['infections'].sum(), "integer"),
        ],
    }
    
    summary_df = pd.DataFrame(summary_stats)
    summary_df = summary_df.fillna("Not available")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
else:
    st.info("Insufficient data for summary statistics")

# Footer
st.markdown("---")
st.markdown(
    "<small>SSI Monitoring Dashboard | Data updated automatically from pipeline</small>",
    unsafe_allow_html=True,
)
