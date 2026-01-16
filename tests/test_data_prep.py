"""Tests for data preparation module."""

import pandas as pd
import pytest

from src.data_prep import coerce_ssi_flag, standardize_category


def test_coerce_ssi_flag_numeric():
    """Test SSI flag coercion with numeric values."""
    # Test with 0/1
    series = pd.Series([0, 1, 0, 1, 0])
    result = coerce_ssi_flag(series)
    assert result.tolist() == [0, 1, 0, 1, 0]
    
    # Test with counts > 1
    series = pd.Series([0, 2, 5, 0, 1])
    result = coerce_ssi_flag(series)
    assert result.tolist() == [0, 1, 1, 0, 1]


def test_coerce_ssi_flag_string():
    """Test SSI flag coercion with string values."""
    # Test Y/N
    series = pd.Series(["Y", "N", "Yes", "No", "y"])
    result = coerce_ssi_flag(series)
    assert result.tolist() == [1, 0, 1, 0, 1]
    
    # Test True/False
    series = pd.Series(["True", "False", "TRUE", "false"])
    result = coerce_ssi_flag(series)
    assert result.tolist() == [1, 0, 1, 0]


def test_standardize_category():
    """Test category standardization."""
    series = pd.Series(["  colon surgery  ", "CARDIAC", "unknown", "", "N/A"])
    result = standardize_category(series)
    assert result.tolist() == ["COLON SURGERY", "CARDIAC", "UNKNOWN", "UNKNOWN", "UNKNOWN"]


def test_month_quarter_derivation():
    """Test month and quarter derivation from dates."""
    dates = pd.Series([
        "2023-01-15",
        "2023-06-20",
        "2023-12-31",
    ])
    dates = pd.to_datetime(dates)
    
    months = dates.dt.to_period("M").astype(str)
    quarters = dates.dt.year.astype(str) + "-Q" + dates.dt.quarter.astype(str)
    
    assert months.tolist() == ["2023-01", "2023-06", "2023-12"]
    assert quarters.tolist() == ["2023-Q1", "2023-Q2", "2023-Q4"]
