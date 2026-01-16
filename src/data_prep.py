"""Data preparation and cleaning module for SSI analytics."""

import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import (
    CATEGORY_COLUMN_PATTERNS,
    DATA_RAW_DIR,
    DATE_COLUMN_PATTERNS,
    SSI_COLUMN_PATTERNS,
    VOLUME_COLUMN_PATTERNS,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_csv_file() -> Optional[Path]:
    """Find the first CSV file in data/raw directory."""
    csv_files = list(DATA_RAW_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {DATA_RAW_DIR}. Please place your SSI dataset there."
        )
    return csv_files[0]


def detect_column(
    df: pd.DataFrame, patterns: list, column_type: str
) -> Optional[str]:
    """Detect column name matching given patterns (case-insensitive).
    
    Prioritizes exact matches and more specific patterns first.
    """
    df_cols_lower = [col.lower() for col in df.columns]
    
    # First pass: look for exact matches (case-insensitive)
    for pattern in patterns:
        pattern_lower = pattern.lower()
        for idx, col_lower in enumerate(df_cols_lower):
            if col_lower == pattern_lower:
                matched_col = df.columns[idx]
                logger.info(f"Detected {column_type} column (exact match): {matched_col}")
                return matched_col
    
    # Second pass: look for substring matches (prioritize patterns in order)
    for pattern in patterns:
        pattern_lower = pattern.lower()
        for idx, col_lower in enumerate(df_cols_lower):
            if pattern_lower in col_lower:
                matched_col = df.columns[idx]
                # For volume columns, verify it's numeric and has reasonable values
                if column_type == "volume":
                    if pd.api.types.is_numeric_dtype(df[matched_col]):
                        # Check if values are reasonable (positive numbers)
                        sample_values = df[matched_col].dropna()
                        if len(sample_values) > 0 and (sample_values > 0).any():
                            logger.info(f"Detected {column_type} column: {matched_col}")
                            return matched_col
                else:
                    logger.info(f"Detected {column_type} column: {matched_col}")
                    return matched_col
    
    logger.warning(f"Could not detect {column_type} column using patterns: {patterns}")
    return None


def coerce_ssi_flag(series: pd.Series) -> pd.Series:
    """Coerce SSI flag to binary 0/1."""
    result = series.copy()
    
    # Handle numeric
    if pd.api.types.is_numeric_dtype(result):
        result = (result > 0).astype(int)
    else:
        # Handle string/object types
        result = result.astype(str).str.strip().str.upper()
        positive_values = ["Y", "YES", "TRUE", "1", "T", "INFECTED", "SSI"]
        result = result.apply(lambda x: 1 if x in positive_values else 0)
    
    return result.astype(int)


def standardize_category(series: pd.Series) -> pd.Series:
    """Standardize category values: trim, uppercase, handle missing."""
    result = series.astype(str).str.strip().str.upper()
    result = result.replace(["", "NAN", "NONE", "NULL", "N/A", "NA"], "UNKNOWN")
    return result


def parse_date_column(series: pd.Series) -> pd.Series:
    """Parse date column with multiple format attempts."""
    result = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
    return result


def expand_aggregated_data(
    df: pd.DataFrame,
    volume_col: str,
    infection_col: str,
    category_col: Optional[str] = None,
) -> pd.DataFrame:
    """Expand aggregated data into individual records.
    
    For each row with Procedure_Count=N and Infection_Count=M,
    creates N individual records with M infections.
    """
    expanded_rows = []
    
    # Filter out rows with missing or invalid volume/infection data
    initial_len = len(df)
    df_clean = df.copy()
    df_clean = df_clean.dropna(subset=[volume_col, infection_col])
    
    # Convert to numeric, coercing errors to NaN
    df_clean[volume_col] = pd.to_numeric(df_clean[volume_col], errors='coerce')
    df_clean[infection_col] = pd.to_numeric(df_clean[infection_col], errors='coerce')
    
    # Filter out rows where volume or infections are NaN, negative, or zero volume
    df_clean = df_clean[
        (df_clean[volume_col].notna()) & 
        (df_clean[volume_col] > 0) &
        (df_clean[infection_col].notna()) &
        (df_clean[infection_col] >= 0)
    ]
    
    if len(df_clean) < initial_len:
        logger.warning(f"Dropped {initial_len - len(df_clean)} rows with invalid volume/infection data")
    
    for idx, row in df_clean.iterrows():
        volume = int(row[volume_col])
        infections = int(row[infection_col])
        
        # Ensure infections doesn't exceed volume
        infections = min(infections, volume)
        
        # Create individual records
        for i in range(volume):
            record = row.copy()
            # Mark as infection if within first M records
            record[infection_col] = 1 if i < infections else 0
            expanded_rows.append(record)
    
    expanded_df = pd.DataFrame(expanded_rows)
    logger.info(f"Expanded {len(df_clean)} aggregated rows to {len(expanded_df)} individual records")
    return expanded_df


def prepare_data(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """Main data preparation function.
    
    Args:
        csv_path: Optional path to CSV file. If None, auto-detects first CSV in data/raw.
    
    Returns:
        Cleaned DataFrame with standardized columns.
    """
    if csv_path is None:
        csv_path = find_csv_file()
    
    logger.info(f"Loading data from {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Detect column types
    date_col = detect_column(df, DATE_COLUMN_PATTERNS, "date")
    ssi_col = detect_column(df, SSI_COLUMN_PATTERNS, "SSI/infection")
    category_col = detect_column(df, CATEGORY_COLUMN_PATTERNS, "category")
    volume_col = detect_column(df, VOLUME_COLUMN_PATTERNS, "volume")
    year_col = detect_column(df, ["year"], "year")  # Detect Year before expansion
    
    # Check if data is aggregated (has volume and infection count columns)
    is_aggregated = volume_col is not None and ssi_col is not None
    
    if is_aggregated and len(df) > 0:
        # Check if ssi_col contains counts (aggregated) vs flags (individual)
        is_count_based = (
            pd.api.types.is_numeric_dtype(df[ssi_col])
            and df[ssi_col].max() > 1
        )
        
        if is_count_based:
            logger.info("Detected aggregated data format. Expanding to individual records...")
            # Expand aggregated data (Year column will be preserved in each row)
            df = expand_aggregated_data(df, volume_col, ssi_col, category_col)
            # After expansion, ssi_col now contains 0/1 flags
    
    # Handle date column
    if date_col:
        df["surgery_date"] = parse_date_column(df[date_col])
    elif year_col:
        logger.info("No date column found, using Year column to create synthetic dates")
        # Ensure Year is numeric and handle any NaN values
        df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
        # Create dates from Year (use mid-year date for each year)
        df["surgery_date"] = pd.to_datetime(
            df[year_col].astype(str).replace('nan', '2017') + "-06-15", 
            errors="coerce"
        )
        # Fill any remaining NaT with a default date
        if df["surgery_date"].isna().any():
            default_year = int(df[year_col].median()) if df[year_col].notna().any() else 2017
            df["surgery_date"] = df["surgery_date"].fillna(pd.Timestamp(f"{default_year}-06-15"))
    else:
        logger.warning("No date or year column found. Creating placeholder dates.")
        df["surgery_date"] = pd.Timestamp("2017-06-15")
    
    # Handle SSI flag
    if ssi_col:
        df["ssi"] = coerce_ssi_flag(df[ssi_col])
    else:
        raise ValueError("Could not detect SSI/infection column. Please check data format.")
    
    # Handle category
    if category_col:
        df["procedure_category"] = standardize_category(df[category_col])
    else:
        logger.warning("No category column found. Using 'UNKNOWN'.")
        df["procedure_category"] = "UNKNOWN"
    
    # Drop rows with missing critical fields
    initial_len = len(df)
    df = df.dropna(subset=["surgery_date", "ssi"])
    if len(df) < initial_len:
        logger.warning(f"Dropped {initial_len - len(df)} rows with missing critical fields")
    
    # Derive time-based fields
    df["year"] = df["surgery_date"].dt.year
    df["month"] = df["surgery_date"].dt.to_period("M").astype(str)
    df["quarter"] = (
        df["surgery_date"].dt.year.astype(str)
        + "-Q"
        + df["surgery_date"].dt.quarter.astype(str)
    )
    
    # Determine initiative split date (median date or documented cut point)
    median_date = df["surgery_date"].median()
    logger.info(f"Using median surgery date {median_date.date()} as initiative split point")
    df["initiative_period"] = (df["surgery_date"] >= median_date).map(
        {True: "post", False: "pre"}
    )
    
    # Select and order final columns
    final_columns = [
        "surgery_date",
        "year",
        "month",
        "quarter",
        "procedure_category",
        "ssi",
        "initiative_period",
    ]
    
    # Keep original columns that might be useful
    original_cols = [col for col in df.columns if col not in final_columns]
    useful_original = []
    for col in ["Facility_Name", "Hospital_Type", "County", "Specialty"]:
        if col in df.columns:
            useful_original.append(col)
    
    final_columns = final_columns + useful_original
    df_clean = df[final_columns].copy()
    
    logger.info(f"Data preparation complete: {len(df_clean)} records")
    logger.info(f"SSI rate: {df_clean['ssi'].mean():.4f} ({df_clean['ssi'].sum()} infections)")
    
    return df_clean


if __name__ == "__main__":
    df = prepare_data()
    print(df.head())
    print(f"\nData shape: {df.shape}")
    print(f"\nSSI rate: {df['ssi'].mean():.4f}")
