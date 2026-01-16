"""Statistical testing module for SSI analytics."""

import logging
from typing import Dict

import numpy as np
import pandas as pd
from scipy import stats

from src.config import ALPHA

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def two_proportion_z_test(
    n1: int, x1: int, n2: int, x2: int
) -> Dict:
    """Perform two-proportion z-test.
    
    Args:
        n1: Sample size for group 1
        x1: Number of successes in group 1
        n2: Sample size for group 2
        x2: Number of successes in group 2
    
    Returns:
        Dictionary with test results
    """
    if n1 == 0 or n2 == 0:
        return {
            "statistic": np.nan,
            "p_value": 1.0,
            "significant": False,
            "error": "Zero sample size",
        }
    
    p1 = x1 / n1
    p2 = x2 / n2
    
    # Pooled proportion
    p_pooled = (x1 + x2) / (n1 + n2)
    
    # Standard error
    se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
    
    if se == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "significant": False,
            "error": "Zero standard error",
        }
    
    # Z-statistic
    z_stat = (p1 - p2) / se
    
    # Two-tailed p-value
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    
    return {
        "statistic": z_stat,
        "p_value": p_value,
        "significant": p_value < ALPHA,
        "p1": p1,
        "p2": p2,
        "difference": p1 - p2,
    }


def chi_square_test(
    n1: int, x1: int, n2: int, x2: int
) -> Dict:
    """Perform chi-square test of independence.
    
    Args:
        n1: Sample size for group 1
        x1: Number of successes in group 1
        n2: Sample size for group 2
        x2: Number of successes in group 2
    
    Returns:
        Dictionary with test results
    """
    # Create contingency table
    #          Success  Failure
    # Group 1    x1     n1-x1
    # Group 2    x2     n2-x2
    
    contingency = np.array([[x1, n1 - x1], [x2, n2 - x2]])
    
    if np.any(contingency < 0):
        return {
            "statistic": np.nan,
            "p_value": 1.0,
            "significant": False,
            "error": "Invalid contingency table",
        }
    
    chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
    
    return {
        "statistic": chi2,
        "p_value": p_value,
        "degrees_of_freedom": dof,
        "significant": p_value < ALPHA,
        "expected": expected.tolist(),
    }


def test_pre_post_comparison(df: pd.DataFrame) -> Dict:
    """Test pre vs post initiative comparison.
    
    Args:
        df: Input DataFrame with initiative_period column
    
    Returns:
        Dictionary with test results
    """
    pre_df = df[df["initiative_period"] == "pre"]
    post_df = df[df["initiative_period"] == "post"]
    
    n1 = len(pre_df)
    x1 = pre_df["ssi"].sum()
    n2 = len(post_df)
    x2 = post_df["ssi"].sum()
    
    # Perform both tests
    z_test = two_proportion_z_test(n1, x1, n2, x2)
    chi2_test = chi_square_test(n1, x1, n2, x2)
    
    return {
        "z_test": z_test,
        "chi2_test": chi2_test,
        "pre_n": n1,
        "pre_infections": x1,
        "post_n": n2,
        "post_infections": x2,
    }
