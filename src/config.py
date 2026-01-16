"""Configuration settings for SSI analytics pipeline."""

from pathlib import Path
from typing import Dict, List

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Column mapping patterns (for flexible CSV detection)
DATE_COLUMN_PATTERNS = [
    "date", "surgery_date", "procedure_date", "op_date", 
    "surgery_dt", "procedure_dt", "operation_date"
]

SSI_COLUMN_PATTERNS = [
    "ssi", "infection", "infected", "outcome", 
    "infection_count", "has_ssi", "ssi_flag"
]

CATEGORY_COLUMN_PATTERNS = [
    "procedure", "proc", "surgery_type", "specialty", 
    "service", "wound", "category", "operative_procedure"
]

VOLUME_COLUMN_PATTERNS = [
    "volume", "count", "procedure_count", "total", "n"
]

# Analysis parameters
MIN_VOLUME_FOR_RATE = 30  # Minimum procedures for rate calculation
PARETO_THRESHOLD = 0.75  # Target cumulative % for Pareto analysis
ALERT_SD_MULTIPLIER = 2.0  # For outlier detection (mean + 2*SD)
ROLLING_WINDOW_MONTHS = 3  # For rolling average calculations

# Statistical test parameters
ALPHA = 0.05  # Significance level

# Visualization settings
FIGURE_DPI = 300
FIGURE_FORMAT = "png"
FIGURE_SIZE = (12, 6)

# Create directories if they don't exist
for dir_path in [DATA_RAW_DIR, DATA_PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
