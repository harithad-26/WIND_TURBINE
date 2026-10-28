# Data Organization Report: Wind Turbine SCADA Dataset
**Project:** AI-Based Predictive Maintenance of Wind Turbines (Machine Learning Powered Early Failure Prediction using SCADA Data)  
**Phase:** Phase 1 - Data Organization & Inspection Workbook Creation  
**Execution Timestamp:** 2026-09-06 23:48:00  

---

## Master Dataset

The **single authoritative master dataset** for this project is:
```
cleaned_data/cleaned_scada_data.parquet
```

This Snappy-compressed Parquet dataset contains the entire sanitized wind turbine SCADA operational corpus.

| Master Dataset Attribute | Verified Empirical Value |
| :--- | :--- |
| **Master Dataset File Path** | `cleaned_data/cleaned_scada_data.parquet` |
| **Storage Format** | Snappy-compressed Apache Parquet |
| **File Size on Disk** | ~91.0 MB |
| **Total Observations (Rows)** | **1,196,747 rows** |
| **Total Features (Columns)** | **84 columns** |
| **Remaining Missing Values (NaN)** | **0** (100% data completeness) |
| **Duplicate Rows** | **0** (0 duplicates found) |

*Note:* All raw dataset files inside `datasets/` remain 100% untouched in their original state.

---

## Asset Distribution

The dataset covers **5 unique physical wind turbine assets** (Asset IDs `0`, `10`, `11`, `13`, `21`). The observation breakdown per turbine is as follows:

| Asset ID | Row Count | Percentage Share (%) | Earliest Timestamp | Latest Timestamp | Time Span |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Asset 0** | 272,477 | 22.77% | 2022-01-01 00:00:00 | 2023-10-22 10:20:00 | ~21.7 months |
| **Asset 10** | 274,213 | 22.91% | 2022-01-01 00:00:00 | 2023-11-20 00:40:00 | ~22.6 months |
| **Asset 11** | 217,950 | 18.21% | 2022-04-04 02:30:00 | 2023-09-21 00:50:00 | ~17.6 months |
| **Asset 13** | 216,543 | 18.09% | 2022-03-03 14:00:00 | 2023-09-13 15:30:00 | ~18.3 months |
| **Asset 21** | 215,564 | 18.01% | 2022-04-30 13:20:00 | 2023-10-21 08:40:00 | ~17.7 months |
| **Total / Overall** | **1,196,747** | **100.00%** | **2022-01-01 00:00:00** | **2023-11-20 00:40:00** | **~22.6 months** |

---

## Time Coverage

* **Complete Time Horizon:** `2022-01-01 00:00:00` to `2023-11-20 00:40:00` (688 calendar days / ~22.6 months).
* **SCADA Resolution:** Continuous 10-minute sampling sequence.
* **Chronological Structure:** Observations are ordered strictly chronologically per `asset_id`.

---

## Train/Test Distribution

The raw dataset contains a pre-segmented protocol column named `train_test`, which demarcates historical continuous SCADA training records from event prediction evaluation windows:

| Protocol Category (`train_test`) | Row Count | Percentage Share (%) | Operational Context |
| :--- | :--- | :--- | :--- |
| `train` | 1,146,154 | 95.77% | Historical baseline SCADA series (~1 year continuous pre-event) |
| `prediction` | 50,593 | 4.23% | High-density event evaluation windows (~1–4 weeks per event) |
| **Total** | **1,196,747** | **100.00%** | Combined SCADA Corpus |

---

## Status Distribution

The turbine operational state code column `status_type_id` documents real-time control system states across the farm:

| Status Code (`status_type_id`) | Row Count | Percentage (%) | Operational Meaning |
| :--- | :--- | :--- | :--- |
| **Code 0** | 1,053,736 | 88.05% | Normal power production state |
| **Code 4** | 119,322 | 9.97% | Fault / Emergency trip / Shutdown state |
| **Code 3** | 23,689 | 1.98% | Warning / Advisory alarm state |
| **Total** | **1,196,747** | **100.00%** | All SCADA State Observations |

---

## Excel Inspection File

A human-readable inspection workbook has been created at:
```
reports/data_preview.xlsx
```

This workbook contains 4 professionally formatted sheets designed for documentation and human auditing without loading all 1.196M rows into Excel:

1. **`Data_Preview`**: A representative sample of 1,000 observations (200 rows per asset_id spaced evenly across time), formatted with bold headers, frozen top pane, Excel auto-filters, formatted timestamps, and proper decimal places.
2. **`Feature_Dictionary`**: Complete structural dictionary listing all metadata and 81 physical sensor features (Description, Unit, Data Type, Source, Relevance, Notes) sourced directly from `feature_description.csv`.
3. **`Dataset_Summary`**: High-level statistical dashboard covering total rows, columns, time spans, distributions, missingness, and file formats.
4. **`Asset_Summary`**: Per-asset breakdown table detailing row counts, time ranges, and `train_test` protocol splits for each turbine.

---

## Planned ML Data Preparation

Future machine learning data preparation will be managed via `src/prepare_data.py`.

* **Future Pipeline Strategy:**
  * Target labels will be created by joining `event_info.csv` using `event_id` and constructing a 48-hour pre-failure look-ahead target window $Y_{\text{early\_warning}} = 1$.
  * Feature engineering will extract thermal deltas ($\Delta T = T_{\text{component}} - T_{\text{ambient}}$), power curve residuals, and rolling time-series statistics (1h, 6h, 24h rolling means/stds).
  * Data partitioning will perform a **chronological / time-based split** (grouped by `asset_id` and `event_id`) to prevent temporal data leakage.

---

## Data Integrity Confirmation

1. **Master Parquet Dataset:** `cleaned_data/cleaned_scada_data.parquet` remains the single authoritative master dataset for all computational workflows.
2. **Excel Function:** `reports/data_preview.xlsx` is strictly an inspection/documentation format for human review.
3. **No Data Discarded:** Exactly 1,196,747 rows were preserved; no observations were discarded during this organization step.
4. **No Splitting Performed:** Train/validation/test splitting has **NOT** yet been performed.
5. **No Feature Selection:** Feature selection has **NOT** yet been performed.
6. **No Labels Created:** Failure target labels have **NOT** yet been created.

---

## Created Artifacts Inventory

Below is the complete list of files created during this phase and their exact disk locations:

1. **Master Cleaned Dataset:** [`cleaned_data/cleaned_scada_data.parquet`](file:///c:/Users/harit/Downloads/WIND_TURBINE_DATASET/cleaned_data/cleaned_scada_data.parquet)
2. **Per-Asset Cleaned Files:**
   * [`cleaned_data/asset_0.parquet`](file:///c:/Users/harit/Downloads/WIND_TURBINE_DATASET/cleaned_data/asset_0.parquet)
   * [`cleaned_data/asset_10.parquet`](file:///c:/Users/harit/Downloads/WIND_TURBINE_DATASET/cleaned_data/asset_10.parquet)
   * [`cleaned_data/asset_11.parquet`](file:///c:/Users/harit/Downloads/WIND_TURBINE_DATASET/cleaned_data/asset_11.parquet)
   * [`cleaned_data/asset_13.parquet`](file:///c:/Users/harit/Downloads/WIND_TURBINE_DATASET/cleaned_data/asset_13.parquet)
   * [`cleaned_data/asset_21.parquet`](file:///c:/Users/harit/Downloads/WIND_TURBINE_DATASET/cleaned_data/asset_21.parquet)
3. **Project Directories:**
   * `analysis_data/`
   * `reports/`
4. **Excel Inspection Workbook:** [`reports/data_preview.xlsx`](file:///c:/Users/harit/Downloads/WIND_TURBINE_DATASET/reports/data_preview.xlsx)
5. **Data Preparation Framework Script:** [`src/prepare_data.py`](file:///c:/Users/harit/Downloads/WIND_TURBINE_DATASET/src/prepare_data.py)
6. **Data Organization Report:** [`reports/data_organization_report.md`](file:///c:/Users/harit/Downloads/WIND_TURBINE_DATASET/reports/data_organization_report.md)
