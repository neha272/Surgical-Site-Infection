"""Main pipeline for SSI analytics."""

import logging
from pathlib import Path
from typing import Dict

import pandas as pd

from src.config import DATA_PROCESSED_DIR, REPORTS_DIR
from src.data_prep import prepare_data
from src.metrics import (
    calculate_category_metrics,
    calculate_overall_metrics,
    calculate_pareto_analysis,
    calculate_pre_post_comparison,
    calculate_temporal_metrics,
    calculate_trend,
    detect_outliers,
)
from src.stats_tests import test_pre_post_comparison
from src.viz import (
    plot_category_rates,
    plot_pareto_chart,
    plot_pre_post_comparison,
    plot_ssi_trend,
    plot_volume_vs_rate_scatter,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def generate_executive_summary(
    overall_metrics: Dict,
    temporal_monthly: pd.DataFrame,
    temporal_quarterly: pd.DataFrame,
    category_metrics: pd.DataFrame,
    pareto_results: Dict,
    pre_post_comparison: Dict,
    pre_post_test: Dict,
    trend_results: Dict,
    outliers: list,
) -> str:
    """Generate executive summary markdown."""
    
    summary = f"""# Executive Summary: Surgical Site Infection (SSI) Monitoring

## Overall Performance

- **Total Procedures**: {overall_metrics['total_procedures']:,}
- **Total Infections**: {overall_metrics['total_infections']:,}
- **Overall SSI Rate**: {overall_metrics['overall_ssi_rate']:.4f} ({overall_metrics['overall_ssi_rate']*100:.2f}%)
- **95% Confidence Interval**: [{overall_metrics['rate_lower_ci']:.4f}, {overall_metrics['rate_upper_ci']:.4f}]

## Temporal Trends (Q1)

### Monthly Analysis
- **Average Monthly SSI Rate**: {temporal_monthly['ssi_rate'].mean():.4f}
- **Trend Direction**: {trend_results['direction'].upper()}
- **Trend Significance**: {'Statistically significant' if trend_results['significant'] else 'Not statistically significant'} (p={trend_results['p_value']:.4f})
- **Outlier Periods Detected**: {len(outliers)} period(s)
"""
    
    if outliers:
        summary += f"  - Outliers: {', '.join(outliers)}\n"
    
    summary += f"""
### Quarterly Analysis
- **Average Quarterly SSI Rate**: {temporal_quarterly['ssi_rate'].mean():.4f}
- **Quarterly Range**: [{temporal_quarterly['ssi_rate'].min():.4f}, {temporal_quarterly['ssi_rate'].max():.4f}]

## High-Risk Categories (Q2)

### Top 10 Categories by SSI Rate (min volume ≥30)
"""
    
    top_10 = category_metrics.head(10)
    for idx, row in top_10.iterrows():
        summary += f"- **{row['procedure_category']}**: {row['ssi_rate']:.4f} ({row['infections']}/{row['total_procedures']} procedures)\n"
    
    summary += f"""
### Top 10 Categories by Infection Count
"""
    top_10_by_count = category_metrics.sort_values('infections', ascending=False).head(10)
    for idx, row in top_10_by_count.iterrows():
        summary += f"- **{row['procedure_category']}**: {row['infections']} infections (rate: {row['ssi_rate']:.4f})\n"
    
    summary += f"""
## Pareto Analysis (Q3)

- **Categories accounting for ~{pareto_results['cumulative_pct']:.1f}% of infections**: {pareto_results['categories_count']} categories
- **Top contributing categories**: {', '.join(pareto_results['top_categories'][:5])}

## Pre vs Post Initiative Comparison (Q4)

### Performance Metrics
- **Pre-Initiative SSI Rate**: {pre_post_comparison['pre']['overall_ssi_rate']:.4f} ({pre_post_comparison['pre']['total_infections']}/{pre_post_comparison['pre']['total_procedures']} procedures)
- **Post-Initiative SSI Rate**: {pre_post_comparison['post']['overall_ssi_rate']:.4f} ({pre_post_comparison['post']['total_infections']}/{pre_post_comparison['post']['total_procedures']} procedures)
- **Absolute Change**: {pre_post_comparison['absolute_change']:+.4f} ({pre_post_comparison['absolute_change']*100:+.2f} percentage points)
- **Relative Change**: {pre_post_comparison['relative_change']:+.1f}%

### Statistical Test Results
- **Two-Proportion Z-Test**:
  - Z-statistic: {pre_post_test['z_test']['statistic']:.4f}
  - P-value: {pre_post_test['z_test']['p_value']:.4f}
  - Significant: {'Yes' if pre_post_test['z_test']['significant'] else 'No'}
  
- **Chi-Square Test**:
  - Chi-square statistic: {pre_post_test['chi2_test']['statistic']:.4f}
  - P-value: {pre_post_test['chi2_test']['p_value']:.4f}
  - Significant: {'Yes' if pre_post_test['chi2_test']['significant'] else 'No'}

**Interpretation**: {'Improvement observed' if pre_post_comparison['improvement'] else 'No improvement observed'} in SSI rates {'with statistical significance' if pre_post_test['z_test']['significant'] else 'without statistical significance'}. Note: Results should be interpreted with caution due to potential confounding factors and case mix differences.

## Monitoring Recommendations (Q5)

### Key Performance Indicators (KPIs)
1. **Monthly SSI Rate**: Target < {overall_metrics['overall_ssi_rate']:.4f} (current overall rate)
2. **Category-Level SSI Rate**: Monitor categories with volume ≥30 procedures
3. **Rolling 3-Month SSI Rate**: Use for trend detection and smoothing
4. **Total Surgeries**: Track volume trends

### Alert Thresholds
- **Outlier Detection**: Monthly rate > mean + 2×SD (current threshold: {temporal_monthly['ssi_rate'].mean() + 2*temporal_monthly['ssi_rate'].std():.4f})
- **Category Alert**: Category rate > overall rate + 2×SD
- **Volume Floor**: Minimum 30 procedures for reliable rate calculation

### Monitoring Frequency
- **Daily**: Track total procedures and infections
- **Weekly**: Review category-level metrics
- **Monthly**: Full analysis with trend assessment
- **Quarterly**: Comprehensive review and reporting

### Control Chart Rules (Suggested)
1. Any point above upper control limit (mean + 3×SD)
2. Two of three consecutive points above upper warning limit (mean + 2×SD)
3. Seven consecutive points above mean
4. Significant trend (p < 0.05 in regression analysis)

---
*Report generated automatically by SSI Analytics Pipeline*
"""
    
    return summary


def run_pipeline():
    """Run the complete SSI analytics pipeline."""
    logger.info("=" * 60)
    logger.info("Starting SSI Analytics Pipeline")
    logger.info("=" * 60)
    
    # Step 1: Data Preparation
    logger.info("\n[Step 1/5] Data Preparation")
    df = prepare_data()
    
    # Save processed data
    parquet_path = DATA_PROCESSED_DIR / "ssi_processed.parquet"
    csv_path = DATA_PROCESSED_DIR / "ssi_processed.csv"
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved processed data: {parquet_path}, {csv_path}")
    
    # Step 2: Calculate Metrics
    logger.info("\n[Step 2/5] Calculating Metrics")
    overall_metrics = calculate_overall_metrics(df)
    temporal_monthly = calculate_temporal_metrics(df, period="month")
    temporal_quarterly = calculate_temporal_metrics(df, period="quarter")
    category_metrics = calculate_category_metrics(df)
    
    # Save metrics tables
    temporal_monthly.to_csv(REPORTS_DIR / "temporal_monthly_metrics.csv", index=False)
    temporal_quarterly.to_csv(REPORTS_DIR / "temporal_quarterly_metrics.csv", index=False)
    category_metrics.to_csv(REPORTS_DIR / "category_metrics.csv", index=False)
    logger.info("Saved metrics tables to reports/")
    
    # Step 3: Advanced Analysis
    logger.info("\n[Step 3/5] Advanced Analysis")
    trend_results = calculate_trend(temporal_monthly)
    outliers = detect_outliers(temporal_monthly)
    pareto_results = calculate_pareto_analysis(category_metrics)
    pre_post_comparison = calculate_pre_post_comparison(df)
    pre_post_test = test_pre_post_comparison(df)
    
    # Step 4: Generate Visualizations
    logger.info("\n[Step 4/5] Generating Visualizations")
    plot_ssi_trend(temporal_monthly, period="month")
    plot_ssi_trend(temporal_quarterly, period="quarter")
    plot_category_rates(category_metrics, top_n=10)
    plot_volume_vs_rate_scatter(category_metrics)
    plot_pre_post_comparison(
        pre_post_comparison["pre"]["overall_ssi_rate"],
        pre_post_comparison["post"]["overall_ssi_rate"],
        (pre_post_comparison["pre"]["rate_lower_ci"], pre_post_comparison["pre"]["rate_upper_ci"]),
        (pre_post_comparison["post"]["rate_lower_ci"], pre_post_comparison["post"]["rate_upper_ci"]),
    )
    plot_pareto_chart(pareto_results["pareto_df"])
    logger.info("Saved all visualizations to reports/figures/")
    
    # Step 5: Generate Executive Summary
    logger.info("\n[Step 5/5] Generating Executive Summary")
    summary = generate_executive_summary(
        overall_metrics,
        temporal_monthly,
        temporal_quarterly,
        category_metrics,
        pareto_results,
        pre_post_comparison,
        pre_post_test,
        trend_results,
        outliers,
    )
    
    summary_path = REPORTS_DIR / "executive_summary.md"
    with open(summary_path, "w") as f:
        f.write(summary)
    logger.info(f"Saved executive summary: {summary_path}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Complete!")
    logger.info("=" * 60)
    logger.info(f"\nKey Results:")
    logger.info(f"  - Overall SSI Rate: {overall_metrics['overall_ssi_rate']:.4f}")
    logger.info(f"  - Trend: {trend_results['direction']}")
    logger.info(f"  - Pre vs Post: {pre_post_comparison['relative_change']:+.1f}% change")
    logger.info(f"\nOutputs:")
    logger.info(f"  - Processed data: {DATA_PROCESSED_DIR}")
    logger.info(f"  - Metrics tables: {REPORTS_DIR}")
    logger.info(f"  - Visualizations: {REPORTS_DIR / 'figures'}")
    logger.info(f"  - Executive summary: {summary_path}")
    
    return {
        "df": df,
        "overall_metrics": overall_metrics,
        "temporal_monthly": temporal_monthly,
        "temporal_quarterly": temporal_quarterly,
        "category_metrics": category_metrics,
        "pareto_results": pareto_results,
        "pre_post_comparison": pre_post_comparison,
        "pre_post_test": pre_post_test,
        "trend_results": trend_results,
    }


if __name__ == "__main__":
    results = run_pipeline()
