"""Tests for metrics calculation module."""

import pandas as pd
import pytest

from src.metrics import calculate_ssi_rate, calculate_overall_metrics


def test_calculate_ssi_rate():
    """Test SSI rate calculation with confidence intervals."""
    # Test with normal case
    rate, lower, upper = calculate_ssi_rate(10, 100)
    assert rate == 0.1
    assert 0 < lower < rate < upper < 1
    
    # Test with zero total
    rate, lower, upper = calculate_ssi_rate(0, 0)
    assert rate == 0.0
    assert lower == 0.0
    assert upper == 0.0
    
    # Test with no infections
    rate, lower, upper = calculate_ssi_rate(0, 100)
    assert rate == 0.0
    assert lower >= 0.0
    assert upper <= 1.0


def test_calculate_overall_metrics():
    """Test overall metrics calculation."""
    # Create sample data
    df = pd.DataFrame({
        "ssi": [0, 1, 0, 1, 0, 0, 1, 0, 0, 0],
        "surgery_date": pd.date_range("2023-01-01", periods=10),
        "procedure_category": ["A"] * 10,
    })
    
    metrics = calculate_overall_metrics(df)
    
    assert metrics["total_procedures"] == 10
    assert metrics["total_infections"] == 3
    assert metrics["overall_ssi_rate"] == 0.3
    assert "rate_lower_ci" in metrics
    assert "rate_upper_ci" in metrics
