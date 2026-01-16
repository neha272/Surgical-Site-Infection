"""Metrics calculation module for SSI analytics."""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from src.config import MIN_VOLUME_FOR_RATE, PARETO_THRESHOLD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_ssi_rate(
    infections: int, total: int, method: str = "wilson"
) -> Tuple[float, float, float]:
    """Calculate SSI rate with confidence interval.
    
    Args:
        infections: Number of infections
        total: Total procedures
        method: CI method ('wilson' or 'normal')
    
    Returns:
        Tuple of (rate, lower_ci, upper_ci)
    """
    if total == 0:
        return (0.0, 0.0, 0.0)
    
    rate = infections / total
    
    if method == "wilson":
        # Wilson score interval
        z = stats.norm.ppf(0.975)  # 95% CI
        denominator = 1 + (z**2 / total)
        center = (rate + (z**2 / (2 * total))) / denominator
        margin = z * np.sqrt((rate * (1 - rate) + z**2 / (4 * total)) / total) / denominator
        lower = max(0, center - margin)
        upper = min(1, center + margin)
    else:
        # Normal approximation
        se = np.sqrt(rate * (1 - rate) / total)
        z = stats.norm.ppf(0.975)
        lower = max(0, rate - z * se)
        upper = min(1, rate + z * se)
    
    return (rate, lower, upper)


def calculate_overall_metrics(df: pd.DataFrame) -> Dict:
    """Calculate overall SSI metrics."""
    total_procedures = len(df)
    total_infections = df["ssi"].sum()
    overall_rate = total_infections / total_procedures if total_procedures > 0 else 0.0
    
    rate, lower_ci, upper_ci = calculate_ssi_rate(total_infections, total_procedures)
    
    return {
        "total_procedures": total_procedures,
        "total_infections": total_infections,
        "overall_ssi_rate": overall_rate,
        "rate_lower_ci": lower_ci,
        "rate_upper_ci": upper_ci,
    }


def calculate_temporal_metrics(df: pd.DataFrame, period: str = "month") -> pd.DataFrame:
    """Calculate SSI rates by time period.
    
    Args:
        df: Input DataFrame
        period: 'month' or 'quarter'
    
    Returns:
        DataFrame with temporal metrics
    """
    period_col = "month" if period == "month" else "quarter"
    
    temporal = df.groupby(period_col).agg(
        total_procedures=("ssi", "count"),
        infections=("ssi", "sum"),
    ).reset_index()
    
    temporal["ssi_rate"] = temporal["infections"] / temporal["total_procedures"]
    
    # Calculate confidence intervals
    ci_results = temporal.apply(
        lambda row: calculate_ssi_rate(row["infections"], row["total_procedures"]),
        axis=1,
    )
    temporal[["rate", "ci_lower", "ci_upper"]] = pd.DataFrame(
        ci_results.tolist(), index=temporal.index
    )
    
    # Calculate rolling average
    if period == "month":
        temporal = temporal.sort_values("month")
        temporal["rolling_3m_rate"] = temporal["ssi_rate"].rolling(
            window=3, min_periods=1
        ).mean()
    
    return temporal


def calculate_category_metrics(
    df: pd.DataFrame, min_volume: int = MIN_VOLUME_FOR_RATE
) -> pd.DataFrame:
    """Calculate SSI rates by procedure category.
    
    Args:
        df: Input DataFrame
        min_volume: Minimum procedures required for rate calculation
    
    Returns:
        DataFrame with category metrics
    """
    category_metrics = df.groupby("procedure_category").agg(
        total_procedures=("ssi", "count"),
        infections=("ssi", "sum"),
    ).reset_index()
    
    category_metrics = category_metrics[
        category_metrics["total_procedures"] >= min_volume
    ]
    
    category_metrics["ssi_rate"] = (
        category_metrics["infections"] / category_metrics["total_procedures"]
    )
    
    # Calculate confidence intervals
    ci_results = category_metrics.apply(
        lambda row: calculate_ssi_rate(row["infections"], row["total_procedures"]),
        axis=1,
    )
    category_metrics[["rate", "ci_lower", "ci_upper"]] = pd.DataFrame(
        ci_results.tolist(), index=category_metrics.index
    )
    
    # Sort by rate (descending)
    category_metrics = category_metrics.sort_values("ssi_rate", ascending=False)
    
    return category_metrics


def detect_outliers(temporal_df: pd.DataFrame, sd_multiplier: float = 2.0) -> List[str]:
    """Detect outlier periods using mean + SD threshold.
    
    Args:
        temporal_df: DataFrame with temporal metrics
        sd_multiplier: Multiplier for standard deviation threshold
    
    Returns:
        List of outlier period labels
    """
    mean_rate = temporal_df["ssi_rate"].mean()
    std_rate = temporal_df["ssi_rate"].std()
    threshold = mean_rate + (sd_multiplier * std_rate)
    
    outliers = temporal_df[temporal_df["ssi_rate"] > threshold]
    return outliers["month"].tolist() if "month" in outliers.columns else outliers["quarter"].tolist()


def calculate_trend(temporal_df: pd.DataFrame) -> Dict:
    """Calculate trend using simple linear regression.
    
    Args:
        temporal_df: DataFrame with temporal metrics (must be sorted by time)
    
    Returns:
        Dictionary with trend metrics
    """
    if len(temporal_df) < 2:
        return {"slope": 0, "p_value": 1.0, "direction": "insufficient_data"}
    
    # Create numeric index for regression
    x = np.arange(len(temporal_df))
    y = temporal_df["ssi_rate"].values
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    
    direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
    
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_value**2,
        "p_value": p_value,
        "direction": direction,
        "significant": p_value < 0.05,
    }


def calculate_pareto_analysis(category_df: pd.DataFrame) -> Dict:
    """Perform Pareto analysis on categories.
    
    Args:
        category_df: DataFrame with category metrics (sorted by infections descending)
    
    Returns:
        Dictionary with Pareto metrics
    """
    # Sort by infections (descending)
    pareto_df = category_df.sort_values("infections", ascending=False).copy()
    pareto_df["cumulative_infections"] = pareto_df["infections"].cumsum()
    total_infections = pareto_df["infections"].sum()
    pareto_df["cumulative_pct"] = (
        pareto_df["cumulative_infections"] / total_infections * 100
    )
    
    # Find categories accounting for threshold % of infections
    threshold_categories = pareto_df[pareto_df["cumulative_pct"] <= PARETO_THRESHOLD * 100]
    
    return {
        "top_categories": threshold_categories["procedure_category"].tolist(),
        "categories_count": len(threshold_categories),
        "cumulative_pct": threshold_categories["cumulative_pct"].max()
        if len(threshold_categories) > 0
        else 0,
        "pareto_df": pareto_df,
    }


def calculate_pre_post_comparison(df: pd.DataFrame) -> Dict:
    """Calculate pre vs post initiative comparison.
    
    Args:
        df: Input DataFrame with initiative_period column
    
    Returns:
        Dictionary with comparison metrics
    """
    pre_df = df[df["initiative_period"] == "pre"]
    post_df = df[df["initiative_period"] == "post"]
    
    pre_metrics = calculate_overall_metrics(pre_df)
    post_metrics = calculate_overall_metrics(post_df)
    
    # Calculate change
    absolute_change = post_metrics["overall_ssi_rate"] - pre_metrics["overall_ssi_rate"]
    relative_change = (
        (absolute_change / pre_metrics["overall_ssi_rate"] * 100)
        if pre_metrics["overall_ssi_rate"] > 0
        else 0
    )
    
    return {
        "pre": pre_metrics,
        "post": post_metrics,
        "absolute_change": absolute_change,
        "relative_change": relative_change,
        "improvement": absolute_change < 0,
    }
