"""
Phase 4 - Steps 4+5: Residuals & Z-score Standardisation [FAST PARALLEL]
========================================================================
Pass MODEL_NAME as sys.argv[1]: "dt", "rf", "xgb"
"""
import json, sys, warnings
import numpy as np, pandas as pd
from pathlib import Path
from joblib import Parallel, delayed

MODEL_NAME = sys.argv[1].lower() if len(sys.argv) > 1 else "dt"
if MODEL_NAME not in ("dt", "rf", "xgb"):
    raise SystemExit(f"Unknown model '{MODEL_NAME}'. Use: dt, rf, xgb")

ROOT        = Path(__file__).resolve().parents[1]
PRED_FILE   = ROOT / "analysis_data" / "phase4" / "nbm" / MODEL_NAME / f"{MODEL_NAME}_predictions.parquet"
META_FILE   = ROOT / "analysis_data" / "phase4" / "nbm" / MODEL_NAME / f"{MODEL_NAME}_model_metadata.csv"
OUT_DIR     = ROOT / "analysis_data" / "phase4" / "residuals" / MODEL_NAME
OUT_DIR.mkdir(parents=True, exist_ok=True)

MIN_SIGMA = 1e-6

def main():
    print(f"=================================================================")
    print(f"  PHASE 4 - STEPS 4+5: RESIDUALS + Z-SCORES [{MODEL_NAME.upper()}]")
    print(f"=================================================================")

    if not PRED_FILE.exists():
        raise FileNotFoundError(f"Prediction file not found: {PRED_FILE}")

    preds_df = pd.read_parquet(PRED_FILE)
    preds_df["raw_residual"] = preds_df["actual_value"] - preds_df["predicted_value"]

    # Compute fold-wise mean and std of normal training residuals using meta_df RMSE as baseline
    meta_df = pd.read_csv(META_FILE)

    # Standardise residuals: z = raw_residual / rmse_train_orig (since mean residual on normal training set is ~0)
    meta_map = dict(zip(zip(meta_df["fold_id"], meta_df["target_column"]), meta_df["rmse_train_orig"]))

    z_records = []
    norm_params = []

    for (fold_id, target_col), group in preds_df.groupby(["fold_id", "target_column"]):
        sigma = meta_map.get((fold_id, target_col), 1.0)
        sigma = max(sigma, MIN_SIGMA)

        norm_params.append({
            "fold_id": fold_id,
            "target_column": target_col,
            "mu_train": 0.0,
            "sigma_train": sigma
        })

    norm_df = pd.DataFrame(norm_params)

    # Vectorized z-score computation
    merged = preds_df.merge(norm_df, on=["fold_id", "target_column"])
    merged["z_score"] = merged["raw_residual"] / merged["sigma_train"]

    # Save raw_residuals.parquet
    raw_df = merged[["fold_id", "independent_event_id", "held_out_event_id", "turbine_uid", "time_stamp", "target_column", "component_group", "event_label", "actual_value", "predicted_value", "raw_residual"]].copy()
    raw_df.to_parquet(OUT_DIR / "raw_residuals.parquet", index=False)

    # Save zscored_residuals.parquet
    z_df = merged[["fold_id", "independent_event_id", "held_out_event_id", "turbine_uid", "time_stamp", "target_column", "component_group", "event_label", "z_score"]].copy()
    z_df.to_parquet(OUT_DIR / "zscored_residuals.parquet", index=False)

    norm_df.to_csv(OUT_DIR / "norm_params.csv", index=False)

    print(f"SUCCESS: Created raw residuals ({len(raw_df)} rows) and z-scores ({len(z_df)} rows) for {MODEL_NAME.upper()}")
    print(f"Saved to {OUT_DIR}")

if __name__ == "__main__":
    main()
