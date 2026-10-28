"""
Phase 4 - Step 6: Generic Event-Level Anomaly Score Aggregation
================================================================
Pass MODEL_NAME as sys.argv[1]: "ridge", "dt", "rf", "xgb"
Default: "ridge"
"""
import json, sys, warnings
import numpy as np, pandas as pd
from pathlib import Path
from datetime import datetime

MODEL_NAME = sys.argv[1].lower() if len(sys.argv) > 1 else "ridge"

ROOT         = Path(__file__).resolve().parents[1]
Z_FILE       = ROOT / "analysis_data" / "phase4" / "residuals" / MODEL_NAME / "zscored_residuals.parquet"
FGROUPS_FILE = ROOT / "analysis_data" / "phase4" / "feature_selection" / "feature_groups.csv"
EVENT_IDX    = ROOT / "analysis_data" / "phase4" / "folds" / "event_index_verified.csv"
FOLDS_FILE   = ROOT / "analysis_data" / "phase4" / "folds" / "loeo_folds.csv"
OUT_DIR      = ROOT / "analysis_data" / "phase4" / "evaluation" / MODEL_NAME
OUT_DIR.mkdir(parents=True, exist_ok=True)

PERSISTENCE_Z_THRESHOLD = 2.5
EXPECTED_EVENTS         = 21
EXPECTED_ANOMALY_EVENTS = 11
EXPECTED_NORMAL_EVENTS  = 10
EXPECTED_COMPONENTS     = 7

def main():
    print(f"\n=======================================================")
    print(f" Phase 4 Step 6 — Event Scores Aggregation ({MODEL_NAME.upper()})")
    print(f"=======================================================")
    
    if not Z_FILE.exists():
        raise FileNotFoundError(f"Input file does not exist: {Z_FILE}")

    z_df = pd.read_parquet(Z_FILE)
    z_df["time_stamp"] = pd.to_datetime(z_df["time_stamp"])
    print(f"Loaded z-scores: {len(z_df)} rows")

    fg_df = pd.read_csv(FGROUPS_FILE)
    fg_df = fg_df[fg_df["in_phase3_data"] == True].copy()
    components = sorted(fg_df["component_group"].unique())

    folds_df = pd.read_csv(FOLDS_FILE)
    folds_df["held_out_event_start"] = pd.to_datetime(folds_df["held_out_event_start"])
    folds_df["held_out_event_end"]   = pd.to_datetime(folds_df["held_out_event_end"])

    # 1. Component scores
    z = z_df.copy()
    z["abs_z"] = z["z_score"].astype(np.float64).abs()

    grp = z.groupby(
        ["fold_id", "independent_event_id", "held_out_event_id",
         "turbine_uid", "component_group", "event_label"]
    )
    comp_records = []
    for (fold_id, ind_eid, held_eid, turbine, comp_grp, ev_label), sub in grp:
        abs_z_vals = sub["abs_z"].values
        comp_records.append({
            "fold_id"              : int(fold_id),
            "independent_event_id" : ind_eid,
            "held_out_event_id"    : held_eid,
            "turbine_uid"          : turbine,
            "component_group"      : comp_grp,
            "event_label"          : ev_label,
            "component_score"      : float(np.median(abs_z_vals)),
            "component_p95"        : float(np.percentile(abs_z_vals, 95)),
            "n_valid_rows"         : len(abs_z_vals),
            "n_valid_timestamps"   : sub["time_stamp"].nunique(),
        })
    comp_df = pd.DataFrame(comp_records).sort_values(["fold_id", "component_group"]).reset_index(drop=True)

    # 2. Per-obs composite score
    within_comp = (
        z.groupby(
            ["fold_id", "independent_event_id", "held_out_event_id",
             "turbine_uid", "event_label", "time_stamp", "component_group"]
        )["abs_z"].mean().reset_index().rename(columns={"abs_z": "comp_mean_abs_z"})
    )
    obs_score = (
        within_comp.groupby(
            ["fold_id", "independent_event_id", "held_out_event_id",
             "turbine_uid", "event_label", "time_stamp"]
        ).agg(
            event_observation_score=("comp_mean_abs_z", "mean"),
            n_components_available=("component_group", "nunique"),
        ).reset_index()
    )

    # 3. Event-level scores
    fold_meta = folds_df[[
        "fold_id", "independent_event_id",
        "held_out_turbine", "held_out_asset_id",
        "held_out_event_start", "held_out_event_end",
        "held_out_event_label", "held_out_rows",
    ]].copy()

    event_records = []
    for _, fold_row in fold_meta.iterrows():
        fold_id   = int(fold_row["fold_id"])
        ind_eid   = fold_row["independent_event_id"]
        turbine   = fold_row["held_out_turbine"]
        asset_id  = int(fold_row["held_out_asset_id"])
        ev_start  = fold_row["held_out_event_start"]
        ev_end    = fold_row["held_out_event_end"]
        ev_label  = fold_row["held_out_event_label"]

        ev_obs = obs_score[obs_score["fold_id"] == fold_id].copy()
        n_valid_obs = len(ev_obs)
        scores_arr = ev_obs["event_observation_score"].values.astype(np.float64) if n_valid_obs > 0 else np.array([])
        n_comp_avail = int(ev_obs["n_components_available"].median()) if n_valid_obs > 0 else 0

        ev_median = float(np.median(scores_arr)) if n_valid_obs > 0 else np.nan
        ev_p95 = float(np.percentile(scores_arr, 95)) if n_valid_obs > 0 else np.nan
        persistence = float((scores_arr > PERSISTENCE_Z_THRESHOLD).sum() / n_valid_obs) if n_valid_obs > 0 else np.nan

        event_records.append({
            "fold_id"                   : fold_id,
            "independent_event_id"      : ind_eid,
            "turbine_uid"               : turbine,
            "asset_id"                  : asset_id,
            "event_start"               : str(ev_start),
            "event_end"                 : str(ev_end),
            "event_label"               : ev_label,
            "n_valid_observations"      : n_valid_obs,
            "n_component_groups_available": n_comp_avail,
            "n_component_groups_missing" : EXPECTED_COMPONENTS - n_comp_avail,
            "event_median_score"         : round(ev_median, 6) if not np.isnan(ev_median) else np.nan,
            "event_p95_score"            : round(ev_p95, 6) if not np.isnan(ev_p95) else np.nan,
            "persistence_score"          : round(persistence, 6) if not np.isnan(persistence) else np.nan,
            "persistence_threshold"      : PERSISTENCE_Z_THRESHOLD,
        })

    event_df = pd.DataFrame(event_records)

    # Save
    for col in ["component_score", "component_p95"]: comp_df[col] = comp_df[col].astype(np.float32)
    comp_df.to_parquet(OUT_DIR / "component_scores.parquet", index=False)

    for col in ["event_median_score", "event_p95_score", "persistence_score"]: event_df[col] = event_df[col].astype(np.float32)
    event_df.to_parquet(OUT_DIR / "event_scores.parquet", index=False)

    print(f"SUCCESS: Saved component and event scores for {MODEL_NAME.upper()} to {OUT_DIR}")

if __name__ == "__main__":
    main()
