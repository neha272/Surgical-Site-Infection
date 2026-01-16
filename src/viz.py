"""Visualization module for SSI analytics."""

import logging
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import FIGURES_DIR, FIGURE_DPI, FIGURE_FORMAT, FIGURE_SIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def save_figure(fig, filename: str, format: str = FIGURE_FORMAT):
    """Save figure to reports/figures directory."""
    output_path = FIGURES_DIR / f"{filename}.{format}"
    try:
        if hasattr(fig, "write_image"):  # Plotly figure
            # Try to save as image, fallback to HTML if kaleido not available
            try:
                fig.write_image(str(output_path), width=FIGURE_SIZE[0] * 100, height=FIGURE_SIZE[1] * 100)
            except Exception as e:
                logger.warning(f"Could not save as {format}, saving as HTML instead: {e}")
                html_path = FIGURES_DIR / f"{filename}.html"
                fig.write_html(str(html_path))
                logger.info(f"Saved figure as HTML: {html_path}")
        else:  # Matplotlib figure
            fig.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
            plt.close(fig)
        logger.info(f"Saved figure: {output_path}")
    except Exception as e:
        logger.error(f"Error saving figure {filename}: {e}")


def plot_ssi_trend(
    temporal_df: pd.DataFrame,
    period: str = "month",
    save: bool = True,
    filename: Optional[str] = None,
):
    """Plot SSI trend over time.
    
    Args:
        temporal_df: DataFrame with temporal metrics
        period: 'month' or 'quarter'
        save: Whether to save the figure
        filename: Optional filename (defaults to ssi_trend_{period})
    """
    period_col = "month" if period == "month" else "quarter"
    
    fig = go.Figure()
    
    # Main trend line
    fig.add_trace(
        go.Scatter(
            x=temporal_df[period_col],
            y=temporal_df["ssi_rate"],
            mode="lines+markers",
            name="SSI Rate",
            line=dict(color="steelblue", width=2),
            marker=dict(size=8),
        )
    )
    
    # Confidence intervals
    fig.add_trace(
        go.Scatter(
            x=temporal_df[period_col],
            y=temporal_df["ci_upper"],
            mode="lines",
            name="Upper CI",
            line=dict(width=0),
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=temporal_df[period_col],
            y=temporal_df["ci_lower"],
            mode="lines",
            name="Lower CI",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(70, 130, 180, 0.2)",
            showlegend=False,
        )
    )
    
    # Rolling average if monthly
    if period == "month" and "rolling_3m_rate" in temporal_df.columns:
        fig.add_trace(
            go.Scatter(
                x=temporal_df[period_col],
                y=temporal_df["rolling_3m_rate"],
                mode="lines",
                name="3-Month Rolling Avg",
                line=dict(color="orange", width=2, dash="dash"),
            )
        )
    
    # Overall benchmark line
    overall_rate = temporal_df["ssi_rate"].mean()
    fig.add_hline(
        y=overall_rate,
        line_dash="dot",
        line_color="gray",
        annotation_text=f"Overall Avg: {overall_rate:.4f}",
    )
    
    fig.update_layout(
        title=f"SSI Rate Trend by {period.capitalize()}",
        xaxis_title=period.capitalize(),
        yaxis_title="SSI Rate",
        hovermode="x unified",
        height=500,
    )
    
    if save:
        filename = filename or f"ssi_trend_{period}"
        save_figure(fig, filename)
    
    return fig


def plot_category_rates(
    category_df: pd.DataFrame,
    top_n: int = 10,
    save: bool = True,
    filename: Optional[str] = None,
):
    """Plot SSI rates by procedure category.
    
    Args:
        category_df: DataFrame with category metrics
        top_n: Number of top categories to show
        save: Whether to save the figure
        filename: Optional filename
    """
    top_categories = category_df.head(top_n).copy()
    top_categories = top_categories.sort_values("ssi_rate", ascending=True)
    
    fig = go.Figure()
    
    # Bar chart with error bars
    fig.add_trace(
        go.Bar(
            x=top_categories["ssi_rate"],
            y=top_categories["procedure_category"],
            orientation="h",
            name="SSI Rate",
            error_x=dict(
                type="data",
                array=top_categories["ci_upper"] - top_categories["ssi_rate"],
                arrayminus=top_categories["ssi_rate"] - top_categories["ci_lower"],
            ),
            marker_color="steelblue",
        )
    )
    
    # Overall benchmark line
    overall_rate = category_df["ssi_rate"].mean()
    fig.add_vline(
        x=overall_rate,
        line_dash="dot",
        line_color="red",
        annotation_text=f"Overall: {overall_rate:.4f}",
    )
    
    fig.update_layout(
        title=f"Top {top_n} Procedure Categories by SSI Rate",
        xaxis_title="SSI Rate",
        yaxis_title="Procedure Category",
        height=max(400, top_n * 40),
        hovermode="closest",
    )
    
    if save:
        filename = filename or "ssi_by_category"
        save_figure(fig, filename)
    
    return fig


def plot_volume_vs_rate_scatter(
    category_df: pd.DataFrame,
    save: bool = True,
    filename: Optional[str] = None,
):
    """Plot volume vs infection rate scatter with annotations.
    
    Args:
        category_df: DataFrame with category metrics
        save: Whether to save the figure
        filename: Optional filename
    """
    fig = go.Figure()
    
    # Scatter plot
    fig.add_trace(
        go.Scatter(
            x=category_df["total_procedures"],
            y=category_df["ssi_rate"],
            mode="markers+text",
            text=category_df["procedure_category"],
            textposition="top center",
            marker=dict(
                size=category_df["infections"],
                sizemode="area",
                sizeref=category_df["infections"].max() / 100,
                color=category_df["ssi_rate"],
                colorscale="Reds",
                showscale=True,
                colorbar=dict(title="SSI Rate"),
            ),
            name="Categories",
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Volume: %{x}<br>"
                "SSI Rate: %{y:.4f}<br>"
                "Infections: %{marker.size}<extra></extra>"
            ),
        )
    )
    
    # Highlight high-risk points (high rate + meaningful volume)
    high_risk = category_df[
        (category_df["ssi_rate"] > category_df["ssi_rate"].quantile(0.75))
        & (category_df["total_procedures"] > category_df["total_procedures"].median())
    ]
    
    if len(high_risk) > 0:
        fig.add_trace(
            go.Scatter(
                x=high_risk["total_procedures"],
                y=high_risk["ssi_rate"],
                mode="markers",
                marker=dict(size=15, color="red", symbol="diamond"),
                name="High Risk",
            )
        )
    
    fig.update_layout(
        title="Procedure Volume vs SSI Rate",
        xaxis_title="Total Procedures (Volume)",
        yaxis_title="SSI Rate",
        hovermode="closest",
        height=600,
    )
    
    if save:
        filename = filename or "volume_vs_rate_scatter"
        save_figure(fig, filename)
    
    return fig


def plot_pre_post_comparison(
    pre_rate: float,
    post_rate: float,
    pre_ci: tuple,
    post_ci: tuple,
    save: bool = True,
    filename: Optional[str] = None,
):
    """Plot pre vs post initiative comparison.
    
    Args:
        pre_rate: Pre-initiative SSI rate
        post_rate: Post-initiative SSI rate
        pre_ci: Pre-initiative confidence interval (lower, upper)
        post_ci: Post-initiative confidence interval (lower, upper)
        save: Whether to save the figure
        filename: Optional filename
    """
    periods = ["Pre-Initiative", "Post-Initiative"]
    rates = [pre_rate, post_rate]
    ci_lower = [pre_ci[0], post_ci[0]]
    ci_upper = [pre_ci[1], post_ci[1]]
    
    fig = go.Figure()
    
    # Bar chart
    fig.add_trace(
        go.Bar(
            x=periods,
            y=rates,
            name="SSI Rate",
            marker_color=["steelblue", "orange"],
            error_y=dict(
                type="data",
                array=[rates[i] - ci_lower[i] for i in range(2)],
                arrayminus=[ci_upper[i] - rates[i] for i in range(2)],
            ),
        )
    )
    
    # Add change annotation
    change = post_rate - pre_rate
    change_pct = (change / pre_rate * 100) if pre_rate > 0 else 0
    fig.add_annotation(
        x=1,
        y=max(rates) * 1.1,
        text=f"Change: {change:+.4f}<br>({change_pct:+.1f}%)",
        showarrow=True,
        arrowhead=2,
    )
    
    fig.update_layout(
        title="Pre vs Post Initiative SSI Rate Comparison",
        yaxis_title="SSI Rate",
        height=500,
    )
    
    if save:
        filename = filename or "pre_post_comparison"
        save_figure(fig, filename)
    
    return fig


def plot_pareto_chart(
    pareto_df: pd.DataFrame,
    save: bool = True,
    filename: Optional[str] = None,
):
    """Plot Pareto chart of infections by category.
    
    Args:
        pareto_df: DataFrame with cumulative percentages
        save: Whether to save the figure
        filename: Optional filename
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Bar chart (infections)
    fig.add_trace(
        go.Bar(
            x=pareto_df["procedure_category"],
            y=pareto_df["infections"],
            name="Infections",
            marker_color="steelblue",
        ),
        secondary_y=False,
    )
    
    # Line chart (cumulative %)
    fig.add_trace(
        go.Scatter(
            x=pareto_df["procedure_category"],
            y=pareto_df["cumulative_pct"],
            mode="lines+markers",
            name="Cumulative %",
            marker=dict(size=8),
            line=dict(color="red", width=2),
        ),
        secondary_y=True,
    )
    
    # Add 80% threshold line
    fig.add_hline(
        y=80,
        line_dash="dot",
        line_color="gray",
        annotation_text="80% Threshold",
        secondary_y=True,
    )
    
    fig.update_xaxes(title_text="Procedure Category", tickangle=-45)
    fig.update_yaxes(title_text="Number of Infections", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative Percentage", secondary_y=True, range=[0, 100])
    
    fig.update_layout(
        title="Pareto Chart: Infections by Procedure Category",
        height=600,
        hovermode="x unified",
    )
    
    if save:
        filename = filename or "pareto_chart"
        save_figure(fig, filename)
    
    return fig
