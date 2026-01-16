# Surgical Site Infection (SSI) Analytics Project

A comprehensive end-to-end analytics system for monitoring Surgical Site Infections (SSI) trends, identifying risk hotspots, and evaluating quality improvement initiatives.

## 🎯 Project Goals

**Primary**: Create a monitoring system to identify SSI trends, risk hotspots, and evaluate whether quality initiatives are effective.

**Secondary**: Define clear KPIs, actionable insights, alert thresholds, and produce executive summaries.

## 📋 Analysis Questions (Q1-Q5)

1. **Q1**: Overall SSI rate & change over time
2. **Q2**: Highest SSI rates by surgical categories
3. **Q3**: Pareto analysis - categories/time periods driving most infections
4. **Q4**: Pre vs post initiative comparison
5. **Q5**: Monitoring recommendations (KPIs, thresholds, frequency)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

1. **Clone or navigate to the project directory**:
```bash
cd Surgical-Site-Infection
```

2. **Create a virtual environment** (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

**Note**: If you're on macOS with Homebrew Python, you may need to use a virtual environment to avoid "externally-managed-environment" errors.

3. **Place your SSI dataset**:
   - Place your CSV file in `data/raw/` directory
   - The pipeline will automatically detect the first CSV file in this directory
   - Supported formats: CSV with columns for date, SSI/infection flag, and procedure category

### Running the Pipeline

**Activate virtual environment** (if using one):
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Run the complete analytics pipeline**:
```bash
python -m src.pipeline
```

This will:
1. Load and clean the raw CSV data
2. Calculate all metrics (overall, temporal, category-level)
3. Perform statistical tests
4. Generate visualizations
5. Create executive summary

**Outputs**:
- `data/processed/ssi_processed.parquet` - Clean processed data
- `data/processed/ssi_processed.csv` - Clean processed data (CSV format)
- `reports/temporal_monthly_metrics.csv` - Monthly metrics table
- `reports/temporal_quarterly_metrics.csv` - Quarterly metrics table
- `reports/category_metrics.csv` - Category-level metrics
- `reports/figures/*.png` - All visualizations
- `reports/executive_summary.md` - Executive summary report

### Running the Dashboard

**Activate virtual environment** (if using one):
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Launch the Streamlit monitoring dashboard**:
```bash
streamlit run app/streamlit_app.py
```

The dashboard provides:
- Real-time KPI tiles (overall rate, last month, rolling 3-month)
- Interactive trend charts
- Category-level analysis
- Volume vs rate scatter plots
- Filtering by date range, category, and specialty

### Running the Analysis Notebook

**Execute the analysis script**:
```bash
python notebooks/ssi_analysis.py
```

This provides detailed answers to Q1-Q5 with printed results and visualizations.

### Running Tests

**Run unit tests**:
```bash
pytest -q
```

Or with verbose output:
```bash
pytest -v
```

## 📁 Repository Structure

```
.
├── app/
│   └── streamlit_app.py          # Streamlit dashboard
├── data/
│   ├── raw/                       # Place your CSV here (gitignored)
│   └── processed/                 # Clean processed data (gitignored)
├── notebooks/
│   └── ssi_analysis.py           # Analysis script (Q1-Q5)
├── reports/
│   ├── figures/                   # Generated visualizations
│   └── executive_summary.md       # Executive summary report
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration settings
│   ├── data_prep.py              # Data cleaning & preparation
│   ├── metrics.py                # Metrics calculations
│   ├── stats_tests.py            # Statistical tests
│   ├── viz.py                    # Visualization functions
│   └── pipeline.py               # Main pipeline
├── tests/
│   ├── test_data_prep.py         # Data prep tests
│   └── test_metrics.py            # Metrics tests
├── .gitignore
├── requirements.txt
└── README.md
```

## 📊 Data Format Expectations

The pipeline is designed to handle flexible CSV formats. It automatically detects:

- **Date column**: Looks for columns containing "date", "surgery_date", "procedure_date", "op_date"
- **SSI/Infection column**: Looks for "ssi", "infection", "infected", "outcome"
- **Category column**: Looks for "procedure", "proc", "surgery_type", "specialty", "service"
- **Volume column** (if aggregated): Looks for "volume", "count", "procedure_count"

### Supported Data Formats

1. **Individual-level data**: One row per surgery with binary SSI flag (0/1, Y/N, True/False)
2. **Aggregated data**: One row per category/time period with procedure counts and infection counts

### Data Handling

- Missing values: Rows with missing critical fields (date, SSI flag) are dropped
- Unknown categories: Standardized to "UNKNOWN"
- Date parsing: Automatic format detection
- SSI flag coercion: Handles 0/1, Y/N, True/False, Yes/No, and numeric counts

## 📈 Key Metrics & KPIs

### Primary KPIs

1. **Overall SSI Rate**: Total infections / Total procedures
2. **Monthly SSI Rate**: Infections per month / Procedures per month
3. **Rolling 3-Month Rate**: Smoothed trend indicator
4. **Category-Level Rate**: SSI rate by procedure category (min volume ≥30)

### Alert Thresholds

- **Outlier Detection**: Monthly rate > mean + 2×SD
- **Category Alert**: Category rate > overall rate + 2×SD
- **Volume Floor**: Minimum 30 procedures for reliable rate calculation

### Monitoring Frequency

- **Daily**: Track total procedures and infections
- **Weekly**: Review category-level metrics
- **Monthly**: Full analysis with trend assessment
- **Quarterly**: Comprehensive review and reporting

## 🔬 Statistical Methods

- **Confidence Intervals**: Wilson score interval for proportions
- **Trend Analysis**: Simple linear regression on monthly rates
- **Pre/Post Comparison**: Two-proportion z-test and chi-square test
- **Outlier Detection**: Mean + 2×SD threshold

## 📝 Outputs Interpretation

### Executive Summary

The `reports/executive_summary.md` file contains:
- Overall performance metrics
- Temporal trend analysis
- High-risk category identification
- Pareto analysis results
- Pre/post initiative comparison with statistical tests
- Monitoring recommendations

### Visualizations

All figures are saved to `reports/figures/`:

1. **ssi_trend_monthly.png**: Monthly SSI rate trend with confidence intervals
2. **ssi_trend_quarterly.png**: Quarterly SSI rate trend
3. **ssi_by_category.png**: Top categories by SSI rate
4. **volume_vs_rate_scatter.png**: Volume vs rate scatter with high-risk annotations
5. **pre_post_comparison.png**: Pre vs post initiative comparison
6. **pareto_chart.png**: Pareto chart of infections by category

### Metrics Tables

CSV files in `reports/`:
- `temporal_monthly_metrics.csv`: Monthly SSI rates with confidence intervals
- `temporal_quarterly_metrics.csv`: Quarterly SSI rates
- `category_metrics.csv`: Category-level metrics sorted by SSI rate

## ⚠️ Important Notes

- **No Clinical Diagnosis**: This system is for population-level quality analytics only, not patient diagnosis or clinical advice.
- **Confounding Factors**: Pre/post comparisons should be interpreted with caution due to potential confounding and case mix differences.
- **Data Quality**: Results depend on data quality and completeness. Review data before analysis.

## 🛠️ Development

### Adding New Metrics

1. Add calculation function to `src/metrics.py`
2. Integrate into `src/pipeline.py`
3. Update executive summary template if needed

### Adding New Visualizations

1. Add plotting function to `src/viz.py`
2. Call from pipeline or dashboard
3. Save to `reports/figures/`

### Running Linter

```bash
# Install development dependencies
pip install black flake8

# Format code
black src/ tests/

# Check style
flake8 src/ tests/
```

## 📄 License

This project is for analytics and monitoring purposes. Ensure compliance with data privacy regulations (HIPAA, GDPR, etc.) when handling patient data.

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new functionality
3. Update documentation
4. Ensure all tests pass

## 📧 Support

For questions or issues, please review the code documentation or create an issue in the repository.

---

**Last Updated**: 2024
**Version**: 1.0.0
