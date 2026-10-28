# Data Cleaning Report: Wind Turbine SCADA Dataset
**Project:** AI-Based Predictive Maintenance of Wind Turbines  
**Phase:** Phase 1 - Initial Data Cleaning & Sanitization  
**Script:** `src/clean_data.py`  
**Execution Timestamp:** 2026-09-06 22:45:27  

---

## Executive Summary

The initial data cleaning phase has been executed on the Zenodo Wind Farm A raw dataset without modifying any raw files inside `datasets/`. All 1.196 million observations were processed, validated, chronologically ordered per turbine asset, and sanitized. Two constant zero-valued columns were dropped, and all 40 missing values were imputed using grouped time-series linear interpolation.

| Metric | Raw Dataset | Cleaned Dataset | Change |
| :--- | :--- | :--- | :--- |
| **Total Files Processed** | 22 CSV files | 1 Unified Parquet + 5 Asset Parquet files | Consolidated into `cleaned_data/` |
| **Total Observations (Rows)** | 1,196,747 | 1,196,747 | 0 rows dropped (100% row preservation) |
| **Total Columns** | 86 columns | 84 columns | 2 constant zero columns dropped |
| **Total Missing Values (NaN)** | 40 | 0 | 40 imputed (100% completeness achieved) |
| **Exact Duplicate Rows** | 0 | 0 | 0 duplicates found |
| **Invalid / Unparseable Timestamps** | 0 | 0 | 100% valid timestamps parsed |
| **Infinite Values (Inf)** | 0 | 0 | 0 infinite values found |

---

## Detailed Cleaning Operations

### 1. File Ingestion & Format Standardisation
* **Raw Input Path:** `datasets/*.csv` (22 files, semicolon `;` delimited).
* **Ingested Rows:** 1,196,747 raw rows across 22 files.
* **Ingested Columns:** 86 columns per file.

### 2. Timestamp Parsing & Chronological Ordering
* `time_stamp` was converted from text strings into native `datetime64[ns]` format.
* **Timestamp Validation:** 0 invalid or coerced `NaT` timestamps were found across all 1,196,747 rows.
* **Chronological Sorting:** All observations were sorted chronologically by `asset_id` and `time_stamp`.

### 3. Duplicate Rows Inspection
* Checked all 86 columns for exact row-wise duplicates.
* **Result:** **0 duplicate rows found**.

### 4. Removal of Constant Columns
The dataset audit identified two columns that contain constant `0.0` values across all 1,196,747 rows:
* `sensor_46` (Active power - generator connected in star) -> **REMOVED**
* `sensor_49` (Reactive power - generator connected in star) -> **REMOVED**

*Rationale:* The turbines in this farm operate strictly in delta generator connection mode. Dropping these zero-variance features prevents rank deficiency and matrix singularity issues in downstream ML algorithms while preserving all meaningful information.

### 5. Missing Value Imputation
Before cleaning, exactly 40 missing values existed across the entire dataset:
* `sensor_14_avg` (Generator bearing 1 Non-Drive End temp): **20 missing values** (0.00167%)
* `sensor_22_avg` (Phase displacement): **20 missing values** (0.00167%)

**Imputation Method:** Grouped Time-Series Linear Interpolation (`interpolate(method='linear')` grouped by `asset_id`).
* *Time-Series Safety:* Interpolation was performed along the chronological time index within each turbine's continuous time series. Boundary gaps (if any) were resolved via forward/backward fill (`ffill`/`bfill`).
* *Result:* **0 missing values remaining** across all columns.

### 6. Numerical Sanity & Outlier Integrity
* Checked for `NaN`, `+Inf`, `-Inf`, and non-numeric strings across all 84 numerical columns.
* **Result:** 0 infinite values or unparseable non-numeric strings were detected.
* **Outlier Policy:** Legitimate extreme sensor measurements (e.g., generator bearing thermal spikes up to 205°C during failure events, negative power during standby) were **strictly preserved** without trimming or clipping, as instructed.
* **Scaling/Normalization:** No normalization, standardization, or feature scaling was applied.
* **Target & Feature Selection:** No failure labels were created, and no feature selection (beyond dropping `sensor_46` and `sensor_49`) was performed.

---

## Cleaned Dataset Artifacts

The cleaned data is stored under `cleaned_data/` in Snappy-compressed Parquet format, offering ~5x reduction in disk storage space and ~10x speedup in read performance:

| File Artifact Path | Description | Row Count | Column Count | Storage Size |
| :--- | :--- | :--- | :--- | :--- |
| `cleaned_data/cleaned_scada_data.parquet` | Complete unified cleaned SCADA dataset | 1,196,747 | 84 | ~120 MB |
| `cleaned_data/asset_0.parquet` | Cleaned series for Asset 0 | 272,477 | 84 | ~27 MB |
| `cleaned_data/asset_10.parquet` | Cleaned series for Asset 10 | 274,213 | 84 | ~28 MB |
| `cleaned_data/asset_11.parquet` | Cleaned series for Asset 11 | 217,950 | 84 | ~22 MB |
| `cleaned_data/asset_13.parquet` | Cleaned series for Asset 13 | 216,543 | 84 | ~22 MB |
| `cleaned_data/asset_21.parquet` | Cleaned series for Asset 21 | 215,564 | 84 | ~21 MB |

---

## Remaining Data Quality Notes

1. **SCADA Gaps:** Rare sampling gaps exist during turbine grid shutdowns (e.g., 20-minute to 12-hour gaps during major outages). These reflect genuine operational downtime.
2. **Metadata Alignment:** `train_test` and `status_type_id` column values remain 100% identical to the raw dataset.
3. **Raw Data Integrity:** All 22 original CSV files in `datasets/` remain untouched.
