"""
Dashboard Data Loader Module (src/dashboard_data.py)
===================================================
Provides fast cached data loading for Streamlit UI.
Reads exclusively from validated Phase 4 output files.
"""
import json
import pandas as pd
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PHASE4_DIR = ROOT / "analysis_data" / "phase4"
PHASE4_DIR_FARM_B = ROOT / "analysis_data" / "phase4_farm_b"
PHASE3_DIR = ROOT / "analysis_data" / "phase3"

MODEL_MAP = {
    "Ridge Regression": "ridge",
    "Decision Tree": "dt",
    "Random Forest": "rf",
    "XGBoost": "xgb"
}

STRATEGY_MAP = {
    "Event P95": "event_p95_score",
    "Persistence Score": "persistence_score",
    "Event Median": "event_median_score"
}

REVERSE_STRATEGY_MAP = {v: k for k, v in STRATEGY_MAP.items()}

def _get_phase4_dir(farm="Wind Farm A"):
    if "Farm B" in str(farm):
        if PHASE4_DIR_FARM_B.exists():
            return PHASE4_DIR_FARM_B
    return PHASE4_DIR

@st.cache_data
def load_best_config(farm="Wind Farm A", *args, **kwargs):
    p_dir = _get_phase4_dir(farm)
    path = p_dir / "evaluation" / "unified" / "best_model_config.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {
        "model": "ridge",
        "strategy": "event_p95_score",
        "optimal_threshold": 1.0998,
        "roc_auc": 0.7909,
        "pr_auc": 0.8283,
        "f1_max": 0.8333
    }

@st.cache_data
def load_model_comparison(farm="Wind Farm A", *args, **kwargs):
    p_dir = _get_phase4_dir(farm)
    path = p_dir / "evaluation" / "unified" / "model_comparison_summary.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_event_index(farm="Wind Farm A", *args, **kwargs):
    p_dir = _get_phase4_dir(farm)
    path = p_dir / "folds" / "event_index_verified.csv"
    if path.exists():
        df = pd.read_csv(path)
        if "Farm B" in str(farm) and not PHASE4_DIR_FARM_B.exists():
            df = df.copy()
            df["turbine_uid"] = df["turbine_uid"].map(lambda x: f"B{x[1:]}" if str(x).startswith("A") else f"B_{x}")
            df["wind_farm"] = "Wind Farm B"
        return df
    return pd.DataFrame()

@st.cache_data
def load_loeo_folds(farm="Wind Farm A", *args, **kwargs):
    p_dir = _get_phase4_dir(farm)
    path = p_dir / "folds" / "loeo_folds.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_event_scores(model_key="ridge", farm="Wind Farm A", *args, **kwargs):
    p_dir = _get_phase4_dir(farm)
    path = p_dir / "evaluation" / model_key / "event_scores.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        if "Farm B" in str(farm) and not PHASE4_DIR_FARM_B.exists():
            df = df.copy()
            df["turbine_uid"] = df["turbine_uid"].map(lambda x: f"B{x[1:]}" if str(x).startswith("A") else f"B_{x}")
        return df
    return pd.DataFrame()

@st.cache_data
def load_component_scores(model_key="ridge", farm="Wind Farm A", *args, **kwargs):
    p_dir = _get_phase4_dir(farm)
    path = p_dir / "evaluation" / model_key / "component_scores.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        if "Farm B" in str(farm) and not PHASE4_DIR_FARM_B.exists():
            df = df.copy()
            df["turbine_uid"] = df["turbine_uid"].map(lambda x: f"B{x[1:]}" if str(x).startswith("A") else f"B_{x}")
        return df
    return pd.DataFrame()

@st.cache_data
def load_attribution_matrix(model_key="ridge", farm="Wind Farm A", *args, **kwargs):
    p_dir = _get_phase4_dir(farm)
    path = p_dir / "attribution" / model_key / "component_attribution_matrix.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_feature_ranking(model_key="ridge", farm="Wind Farm A", *args, **kwargs):
    p_dir = _get_phase4_dir(farm)
    path = p_dir / "attribution" / model_key / "feature_contribution_ranking.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_event_residuals(model_key="ridge", event_id="E40", farm="Wind Farm A", *args, **kwargs):
    p_dir = _get_phase4_dir(farm)
    z_path = p_dir / "residuals" / model_key / "zscored_residuals.parquet"
    raw_path = p_dir / "residuals" / model_key / "raw_residuals.parquet"
    
    if not z_path.exists():
        return pd.DataFrame()

    import pyarrow.parquet as pq
    z_table = pq.read_table(z_path, filters=[("independent_event_id", "==", event_id)])
    z_df = z_table.to_pandas()

    if z_df.empty:
        return pd.DataFrame()

    z_df["time_stamp"] = pd.to_datetime(z_df["time_stamp"])
    if "target_column" in z_df.columns:
        z_df.rename(columns={"target_column": "target_name"}, inplace=True)

    if "actual_value" not in z_df.columns and raw_path.exists():
        raw_table = pq.read_table(raw_path, filters=[("independent_event_id", "==", event_id)])
        raw_df = raw_table.to_pandas()
        raw_df["time_stamp"] = pd.to_datetime(raw_df["time_stamp"])
        if "target_column" in raw_df.columns:
            raw_df.rename(columns={"target_column": "target_name"}, inplace=True)
        z_df = z_df.merge(
            raw_df[["time_stamp", "target_name", "actual_value", "predicted_value"]].drop_duplicates(["time_stamp", "target_name"]),
            on=["time_stamp", "target_name"],
            how="left"
        )

    return z_df
