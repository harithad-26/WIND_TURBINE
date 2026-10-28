"""
Phase 4 - Step 3: Random Forest Normal Behaviour Model (NBM) [HIGH-SPEED OPTIMIZED]
====================================================================================
"""
import json, warnings
import numpy as np, pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT        = Path(__file__).resolve().parents[1]
PHASE3_FILE = ROOT / "analysis_data" / "phase3" / "engineered_features.parquet"
FEAT_SEL    = ROOT / "analysis_data" / "phase4" / "feature_selection" / "selected_features.csv"
FOLDS_FILE  = ROOT / "analysis_data" / "phase4" / "folds" / "loeo_folds.csv"
OUT_DIR     = ROOT / "analysis_data" / "phase4" / "nbm" / "rf"
OUT_DIR.mkdir(parents=True, exist_ok=True)

COL_TIME, COL_TURB, COL_ASSET, COL_STATUS = "time_stamp", "turbine_uid", "asset_id", "status_type_id"
NORMAL_STATUS  = 0
MIN_TRAIN_ROWS = 100

def load_feature_roles():
    sf = pd.read_csv(FEAT_SEL)
    conditioning = sf[sf["role"] == "CONDITIONING"]["column"].tolist()
    targets_df   = sf[sf["role"] == "TARGET"][["column", "component_group"]]
    targets      = dict(zip(targets_df["column"], targets_df["component_group"]))
    return conditioning, targets

def load_phase3(conditioning, targets):
    import pyarrow.parquet as pq
    schema_cols  = pq.read_schema(PHASE3_FILE).names
    cols_to_load = [c for c in [COL_TIME, COL_TURB, COL_ASSET, COL_STATUS] + conditioning + list(targets.keys()) if c in schema_cols]
    df = pd.read_parquet(PHASE3_FILE, columns=cols_to_load)
    df[COL_TIME] = pd.to_datetime(df[COL_TIME])
    return df

def fit_rf_target(target_col, X_tr_scaled, y_tr, X_ho_scaled, y_scaler):
    model = RandomForestRegressor(n_estimators=30, max_depth=5, random_state=42, n_jobs=-1)
    model.fit(X_tr_scaled, y_tr)
    
    pred_tr_scaled = model.predict(X_tr_scaled)
    pred_ho_scaled = model.predict(X_ho_scaled)
    
    pred_tr_orig = y_scaler.inverse_transform(pred_tr_scaled.reshape(-1, 1)).ravel()
    pred_ho_orig = y_scaler.inverse_transform(pred_ho_scaled.reshape(-1, 1)).ravel()
    
    y_tr_orig = y_scaler.inverse_transform(y_tr.reshape(-1, 1)).ravel()
    res_tr_orig = y_tr_orig - pred_tr_orig
    rmse_tr_orig = float(np.sqrt(np.mean(res_tr_orig**2)))
    
    return {
        "target_col": target_col,
        "n_estimators": 30,
        "max_depth": 5,
        "rmse_tr_orig": rmse_tr_orig,
        "pred_ho_orig": pred_ho_orig
    }

def main():
    print("=================================================================")
    print("  PHASE 4 - STEP 3: RANDOM FOREST NBM [HIGH-SPEED]")
    print("=================================================================")
    conditioning, targets = load_feature_roles()
    df = load_phase3(conditioning, targets)
    folds_df = pd.read_csv(FOLDS_FILE)
    folds_df["held_out_event_start"] = pd.to_datetime(folds_df["held_out_event_start"])
    folds_df["held_out_event_end"]   = pd.to_datetime(folds_df["held_out_event_end"])

    pred_records = []
    metadata_records = []

    for idx, fold in folds_df.iterrows():
        fold_id  = int(fold["fold_id"])
        ind_eid  = fold["independent_event_id"]
        turbine  = fold["held_out_turbine"]
        ev_start = fold["held_out_event_start"]
        ev_end   = fold["held_out_event_end"]
        ev_label = fold["held_out_event_label"]

        ho_mask = (df[COL_TURB] == turbine) & (df[COL_TIME] >= ev_start) & (df[COL_TIME] <= ev_end)
        tr_mask = (df[COL_TURB] == turbine) & (df[COL_STATUS] == NORMAL_STATUS) & (~ho_mask)

        tr_df = df[tr_mask].copy()
        ho_df = df[ho_mask].copy()

        scaler_x = StandardScaler()
        X_tr_scaled = scaler_x.fit_transform(tr_df[conditioning].fillna(0).values)
        X_ho_scaled = scaler_x.transform(ho_df[conditioning].fillna(0).values)

        print(f"Fold {fold_id:2d} [{ind_eid:12s}] turbine={turbine} label={ev_label:8s} train={len(tr_df):6d} heldout={len(ho_df):5d}")

        target_cols = list(targets.keys())
        ho_times = ho_df[COL_TIME].values
        ho_actuals = {tc: ho_df[tc].values for tc in target_cols}

        for t_col in target_cols:
            y_tr_raw = tr_df[t_col].values
            valid = ~np.isnan(y_tr_raw)
            if valid.sum() < MIN_TRAIN_ROWS: continue
            
            y_scaler = StandardScaler()
            y_tr_scaled = y_scaler.fit_transform(y_tr_raw[valid].reshape(-1, 1)).ravel()
            X_tr_sub = X_tr_scaled[valid]
            
            res = fit_rf_target(t_col, X_tr_sub, y_tr_scaled, X_ho_scaled, y_scaler)
            comp_grp = targets[t_col]
            
            metadata_records.append({
                "fold_id": fold_id, "independent_event_id": ind_eid, "turbine_uid": turbine,
                "target_column": t_col, "component_group": comp_grp,
                "n_estimators": res["n_estimators"], "max_depth": res["max_depth"], "rmse_train_orig": res["rmse_tr_orig"]
            })

            preds = res["pred_ho_orig"]
            acts  = ho_actuals[t_col]

            for t_val, act_val, pred_val in zip(ho_times, acts, preds):
                pred_records.append({
                    "fold_id": fold_id, "independent_event_id": ind_eid, "held_out_event_id": fold["held_out_event_id"],
                    "turbine_uid": turbine, "time_stamp": t_val, "target_column": t_col,
                    "component_group": comp_grp, "event_label": ev_label,
                    "actual_value": float(act_val) if not np.isnan(act_val) else np.nan,
                    "predicted_value": float(pred_val)
                })

    pred_df = pd.DataFrame(pred_records)
    meta_df = pd.DataFrame(metadata_records)

    pred_df.to_parquet(OUT_DIR / "rf_predictions.parquet", index=False)
    meta_df.to_csv(OUT_DIR / "rf_model_metadata.csv", index=False)
    print(f"\nSUCCESS: Saved RF predictions ({len(pred_df)} rows) and metadata ({len(meta_df)} rows) to {OUT_DIR}")

if __name__ == "__main__":
    main()
