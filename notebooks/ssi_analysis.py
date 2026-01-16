"""
SSI Analysis Notebook (Python script version)

This script performs comprehensive analysis of Surgical Site Infections (SSI) data.
Run this after executing the pipeline to explore the data and answer Q1-Q5.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.config import DATA_PROCESSED_DIR
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

print("=" * 60)
print("SSI Analysis - Answering Q1-Q5")
print("=" * 60)

# Load processed data
csv_path = DATA_PROCESSED_DIR / "ssi_processed.csv"
if not csv_path.exists():
    print(f"ERROR: Processed data not found at {csv_path}")
    print("Please run the pipeline first: python -m src.pipeline")
    sys.exit(1)

df = pd.read_csv(csv_path)
df["surgery_date"] = pd.to_datetime(df["surgery_date"])
print(f"\nLoaded {len(df):,} records")

# Q1: Overall SSI rate & change over time
print("\n" + "=" * 60)
print("Q1: Overall SSI Rate & Change Over Time")
print("=" * 60)

overall_metrics = calculate_overall_metrics(df)
print(f"\nOverall SSI Rate: {overall_metrics['overall_ssi_rate']:.4f} ({overall_metrics['overall_ssi_rate']*100:.2f}%)")
print(f"Total Procedures: {overall_metrics['total_procedures']:,}")
print(f"Total Infections: {overall_metrics['total_infections']:,}")
print(f"95% CI: [{overall_metrics['rate_lower_ci']:.4f}, {overall_metrics['rate_upper_ci']:.4f}]")

# Monthly analysis
temporal_monthly = calculate_temporal_metrics(df, period="month")
print(f"\nMonthly SSI Rates:")
print(temporal_monthly[["month", "total_procedures", "infections", "ssi_rate"]].to_string(index=False))

# Quarterly analysis
temporal_quarterly = calculate_temporal_metrics(df, period="quarter")
print(f"\nQuarterly SSI Rates:")
print(temporal_quarterly[["quarter", "total_procedures", "infections", "ssi_rate"]].to_string(index=False))

# Trend analysis
trend_results = calculate_trend(temporal_monthly)
print(f"\nTrend Analysis:")
print(f"  Direction: {trend_results['direction']}")
print(f"  Slope: {trend_results['slope']:.6f}")
print(f"  R-squared: {trend_results['r_squared']:.4f}")
print(f"  P-value: {trend_results['p_value']:.4f}")
print(f"  Significant: {trend_results['significant']}")

# Outlier detection
outliers = detect_outliers(temporal_monthly)
if outliers:
    print(f"\nOutlier Periods Detected: {outliers}")
else:
    print("\nNo outlier periods detected")

# Generate visualizations
plot_ssi_trend(temporal_monthly, period="month", filename="q1_trend_monthly")
plot_ssi_trend(temporal_quarterly, period="quarter", filename="q1_trend_quarterly")

# Q2: Highest SSI rates by surgical categories
print("\n" + "=" * 60)
print("Q2: Highest SSI Rates by Surgical Categories")
print("=" * 60)

category_metrics = calculate_category_metrics(df, min_volume=30)
print(f"\nTop 10 Categories by SSI Rate (min volume ≥30):")
top_10 = category_metrics.head(10)
for idx, row in top_10.iterrows():
    print(f"  {row['procedure_category']}: {row['ssi_rate']:.4f} ({row['infections']}/{row['total_procedures']})")

print(f"\nTop 10 Categories by Infection Count:")
top_10_by_count = category_metrics.sort_values("infections", ascending=False).head(10)
for idx, row in top_10_by_count.iterrows():
    print(f"  {row['procedure_category']}: {row['infections']} infections (rate: {row['ssi_rate']:.4f})")

plot_category_rates(category_metrics, top_n=10, filename="q2_category_rates")

# Q3: Pareto analysis
print("\n" + "=" * 60)
print("Q3: Pareto Analysis - Categories Driving Most Infections")
print("=" * 60)

pareto_results = calculate_pareto_analysis(category_metrics)
print(f"\nCategories accounting for ~{pareto_results['cumulative_pct']:.1f}% of infections:")
print(f"  Number of categories: {pareto_results['categories_count']}")
print(f"  Top categories: {', '.join(pareto_results['top_categories'][:10])}")

plot_pareto_chart(pareto_results["pareto_df"], filename="q3_pareto_chart")
plot_volume_vs_rate_scatter(category_metrics, filename="q3_volume_vs_rate")

# Q4: Pre vs post initiative comparison
print("\n" + "=" * 60)
print("Q4: Pre vs Post Initiative Comparison")
print("=" * 60)

pre_post_comparison = calculate_pre_post_comparison(df)
print(f"\nPre-Initiative:")
print(f"  SSI Rate: {pre_post_comparison['pre']['overall_ssi_rate']:.4f}")
print(f"  Procedures: {pre_post_comparison['pre']['total_procedures']:,}")
print(f"  Infections: {pre_post_comparison['pre']['total_infections']:,}")

print(f"\nPost-Initiative:")
print(f"  SSI Rate: {pre_post_comparison['post']['overall_ssi_rate']:.4f}")
print(f"  Procedures: {pre_post_comparison['post']['total_procedures']:,}")
print(f"  Infections: {pre_post_comparison['post']['total_infections']:,}")

print(f"\nChange:")
print(f"  Absolute: {pre_post_comparison['absolute_change']:+.4f}")
print(f"  Relative: {pre_post_comparison['relative_change']:+.1f}%")
print(f"  Improvement: {pre_post_comparison['improvement']}")

# Statistical tests
pre_post_test = test_pre_post_comparison(df)
print(f"\nStatistical Tests:")
print(f"  Two-Proportion Z-Test:")
print(f"    Z-statistic: {pre_post_test['z_test']['statistic']:.4f}")
print(f"    P-value: {pre_post_test['z_test']['p_value']:.4f}")
print(f"    Significant: {pre_post_test['z_test']['significant']}")
print(f"  Chi-Square Test:")
print(f"    Chi-square: {pre_post_test['chi2_test']['statistic']:.4f}")
print(f"    P-value: {pre_post_test['chi2_test']['p_value']:.4f}")
print(f"    Significant: {pre_post_test['chi2_test']['significant']}")

plot_pre_post_comparison(
    pre_post_comparison["pre"]["overall_ssi_rate"],
    pre_post_comparison["post"]["overall_ssi_rate"],
    (pre_post_comparison["pre"]["rate_lower_ci"], pre_post_comparison["pre"]["rate_upper_ci"]),
    (pre_post_comparison["post"]["rate_lower_ci"], pre_post_comparison["post"]["rate_upper_ci"]),
    filename="q4_pre_post_comparison",
)

# Q5: Monitoring recommendations
print("\n" + "=" * 60)
print("Q5: Monitoring Recommendations")
print("=" * 60)

print("\nKey Performance Indicators (KPIs):")
print(f"  1. Monthly SSI Rate: Target < {overall_metrics['overall_ssi_rate']:.4f}")
print(f"  2. Category-Level SSI Rate: Monitor categories with volume ≥30")
print(f"  3. Rolling 3-Month SSI Rate: Use for trend detection")
print(f"  4. Total Surgeries: Track volume trends")

print("\nAlert Thresholds:")
mean_rate = temporal_monthly["ssi_rate"].mean()
std_rate = temporal_monthly["ssi_rate"].std()
print(f"  Outlier Detection: Monthly rate > {mean_rate + 2*std_rate:.4f} (mean + 2×SD)")
print(f"  Category Alert: Category rate > overall rate + 2×SD")

print("\nMonitoring Frequency:")
print("  - Daily: Track total procedures and infections")
print("  - Weekly: Review category-level metrics")
print("  - Monthly: Full analysis with trend assessment")
print("  - Quarterly: Comprehensive review and reporting")

print("\n" + "=" * 60)
print("Analysis Complete!")
print("=" * 60)
print("\nAll visualizations saved to reports/figures/")
print("See executive_summary.md for detailed findings")
