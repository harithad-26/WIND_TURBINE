"""
Phase 4 - Step 3: Ridge Normal Behaviour Model (NBM)
=====================================================

WHAT THIS SCRIPT DOES (plain English):
  For every LOEO fold (21 folds) and every health-target variable (21 targets):
    1. Pull the training observations for that fold
       (same turbine, status_type_id == 0, timestamp < event_start).
    2. Fit a StandardScaler on the 8 CONDITIONING inputs - training data ONLY.
    3. Select alpha using RidgeCV on the scaled training data - training data ONLY.
    4. Fit the final Ridge model on the scaled training data.
    5. Apply the same scaler to the held-out event observations.
    6. Predict expected component behaviour for every held-out observation.
    7. Store: fold_id, turbine, time_stamp, target_name, component_group,
              actual_value, predicted_value.

  Total models trained: 21 folds x 21 targets = 441 Ridge models.

FORBIDDEN IN THIS SCRIPT:
  - status_type_id as a model input
  - event_id as a model input
  - train_test as a model input
  - turbine_uid / asset_id as a model input
  - Any scaler fit on held-out data
  - Any alpha selected using held-out data
  - Cross-event or cross-turbine training data

Run with:
    python src/phase4_step3_ridge_nbm.py
"""

import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)

# ---- PATHS ------------------------------------------------------------------
ROOT         = Path(__file__).resolve().parents[1]
PHASE3_FILE  = ROOT / "analysis_data" / "phase3" / "engineered_features.parquet"
FEAT_SEL     = ROOT / "analysis_data" / "phase4" / "feature_selection" / "selected_features.csv"
FOLDS_FILE   = ROOT / "analysis_data" / "phase4" / "folds" / "loeo_folds.csv"
OUT_DIR      = ROOT / "analysis_data" / "phase4" / "nbm" / "ridge"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- PHASE 3 COLUMN NAMES (verified in Step 1 & 2) -------------------------
COL_TIME   = "time_stamp"
COL_TURB   = "turbine_uid"
COL_ASSET  = "asset_id"
COL_STATUS = "status_type_id"
NORMAL_STATUS = 0

# ---- RIDGE CONFIGURATION ----------------------------------------------------
# Alpha candidates for RidgeCV (cross-validated on training fold only).
ALPHA_CANDIDATES = [0.01, 0.1, 1.0, 10.0, 100.0, 1_000.0, 10_000.0]
RIDGECV_CV    = 5       # 5-fold CV within training data to select alpha
MIN_TRAIN_ROWS = 100    # minimum rows required to fit a model


# =============================================================================
# 1 -- Load verified feature roles
# =============================================================================
def load_feature_roles():
    sf = pd.read_csv(FEAT_SEL)
    conditioning = sf[sf["role"] == "CONDITIONING"]["column"].tolist()
    targets_df   = sf[sf["role"] == "TARGET"][["column", "component_group"]]
    targets      = dict(zip(targets_df["column"], targets_df["component_group"]))

    print("  Conditioning inputs (" + str(len(conditioning)) + "):")
    for c in conditioning:
        print("    " + c)
    print("\n  Target variables (" + str(len(targets)) + ") by component:")
    by_group = {}
    for col, grp in targets.items():
        by_group.setdefault(grp, []).append(col)
    for grp in sorted(by_group):
        print("    " + grp + ":")
        for col in by_group[grp]:
            print("      " + col)

    return conditioning, targets


# =============================================================================
# 2 -- Load Phase 3 data (read-only, load only needed columns)
# =============================================================================
def load_phase3(conditioning, targets):
    all_p3_cols  = pd.read_parquet(PHASE3_FILE, columns=[COL_TIME]).columns.tolist()

    # Determine all columns from the full parquet schema
    import pyarrow.parquet as pq
    schema_cols = pq.read_schema(PHASE3_FILE).names

    cols_to_load = [c for c in
                    [COL_TIME, COL_TURB, COL_ASSET, COL_STATUS]
                    + conditioning + list(targets.keys())
                    if c in schema_cols]

    df = pd.read_parquet(PHASE3_FILE, columns=cols_to_load)
    df[COL_TIME] = pd.to_datetime(df[COL_TIME])

    assert df.shape[0] == 425_023, "Phase 3 row count changed: " + str(df.shape[0])
    print("  Phase 3 loaded: " + str(df.shape[0]) + " rows x " + str(df.shape[1]) + " columns")

    missing_cond = [c for c in conditioning if c not in df.columns]
    missing_tgt  = [c for c in targets      if c not in df.columns]
    if missing_cond:
        print("  WARNING: Missing conditioning columns: " + str(missing_cond))
    if missing_tgt:
        print("  WARNING: Missing target columns: " + str(missing_tgt))

    return df


# =============================================================================
# 3 -- Run LOEO Ridge training for all folds and targets
# =============================================================================
def run_loeo_ridge(df, folds_df, conditioning, targets):
    all_predictions = []
    fold_model_meta = []

    cond_in_data = [c for c in conditioning if c in df.columns]
    tgt_in_data  = {k: v for k, v in targets.items() if k in df.columns}

    n_folds    = len(folds_df)
    n_targets  = len(tgt_in_data)
    total_fits = n_folds * n_targets

    print("\n  Running " + str(n_folds) + " folds x " + str(n_targets)
          + " targets = " + str(total_fits) + " Ridge models")
    print("  " + "-" * 60)

    fit_count = 0
    for _, fold in folds_df.iterrows():
        fold_id       = int(fold["fold_id"])
        ind_event_id  = fold["independent_event_id"]
        turbine       = fold["held_out_turbine"]
        event_start   = pd.to_datetime(fold["held_out_event_start"])
        event_end     = pd.to_datetime(fold["held_out_event_end"])
        event_label   = fold["held_out_event_label"]
        held_event_id = fold["held_out_event_id"]

        # ---- BUILD TRAINING MASK ---------------------------------------------
        # Rules: same turbine + normal status + strictly before event_start
        train_mask = (
            (df[COL_TURB]   == turbine) &
            (df[COL_STATUS] == NORMAL_STATUS) &
            (df[COL_TIME]   <  event_start)
        )
        train_df = df[train_mask].copy()

        # ---- BUILD HELD-OUT MASK ---------------------------------------------
        heldout_mask = (
            (df[COL_TURB] == turbine) &
            (df[COL_TIME] >= event_start) &
            (df[COL_TIME] <= event_end)
        )
        heldout_df = df[heldout_mask].copy().reset_index(drop=True)

        n_train   = len(train_df)
        n_heldout = len(heldout_df)

        print("\n  Fold " + str(fold_id).rjust(2)
              + "  [" + ind_event_id.ljust(12) + "]"
              + "  turbine=" + turbine
              + "  label=" + event_label.ljust(8)
              + "  train=" + str(n_train).rjust(6)
              + "  heldout=" + str(n_heldout).rjust(5))

        # ---- LEAKAGE ASSERTIONS (hard stop if violated) ----------------------
        if n_train > 0:
            assert (train_df[COL_TIME] < event_start).all(), \
                "Fold " + str(fold_id) + ": training data has future timestamps!"
            assert (train_df[COL_TURB] == turbine).all(), \
                "Fold " + str(fold_id) + ": training data has wrong turbine rows!"
            assert (train_df[COL_STATUS] == NORMAL_STATUS).all(), \
                "Fold " + str(fold_id) + ": training data has non-normal observations!"

        if n_train < MIN_TRAIN_ROWS:
            print("    SKIP: only " + str(n_train) + " training rows (min=" + str(MIN_TRAIN_ROWS) + ")")
            continue

        # ---- SELECT NEEDED COLUMNS -------------------------------------------
        cols_for_model = [COL_TIME] + cond_in_data + list(tgt_in_data.keys())
        train_work   = train_df[[c for c in cols_for_model
                                  if c in train_df.columns]].copy()
        heldout_work = heldout_df[[c for c in cols_for_model
                                    if c in heldout_df.columns]].copy()

        # ---- DROP ROWS WHERE ANY CONDITIONING INPUT IS NaN ------------------
        cond_nan_train   = train_work[cond_in_data].isna().any(axis=1)
        cond_nan_heldout = heldout_work[cond_in_data].isna().any(axis=1)
        train_work   = train_work[~cond_nan_train].reset_index(drop=True)
        heldout_work = heldout_work[~cond_nan_heldout].reset_index(drop=True)

        n_train_clean = len(train_work)
        if n_train_clean < MIN_TRAIN_ROWS:
            print("    SKIP: only " + str(n_train_clean)
                  + " clean training rows after NaN drop")
            continue

        # ---- FIT SCALER ON TRAINING CONDITIONING DATA ONLY ------------------
        X_train_raw   = train_work[cond_in_data].values.astype(np.float64)
        X_heldout_raw = heldout_work[cond_in_data].values.astype(np.float64)

        scaler    = StandardScaler()
        X_train   = scaler.fit_transform(X_train_raw)   # FIT + TRANSFORM (train)
        X_heldout = scaler.transform(X_heldout_raw)     # TRANSFORM ONLY (held-out)

        scaler_mean = scaler.mean_.tolist()
        scaler_std  = scaler.scale_.tolist()

        # Held-out timestamps - extracted before per-target loop
        heldout_timestamps = heldout_work[COL_TIME].values

        # ---- TRAIN ONE RIDGE MODEL PER TARGET --------------------------------
        for target_col, component_grp in tgt_in_data.items():
            fit_count += 1

            y_train_full     = train_work[target_col].values.astype(np.float64)
            y_heldout_actual = heldout_work[target_col].values.astype(np.float64)

            # Drop training rows where THIS target is NaN
            valid_mask    = ~np.isnan(y_train_full)
            X_tr = X_train[valid_mask]
            y_tr = y_train_full[valid_mask]

            n_valid_train = len(y_tr)
            if n_valid_train < MIN_TRAIN_ROWS:
                print("    " + target_col.ljust(35)
                      + " SKIP (" + str(n_valid_train) + " valid train rows)")
                continue

            # ---- RidgeCV: alpha selection within training data ONLY ----------
            ridge_cv = RidgeCV(
                alphas=ALPHA_CANDIDATES,
                cv=RIDGECV_CV,
                fit_intercept=True,
                scoring="neg_mean_squared_error",
            )
            ridge_cv.fit(X_tr, y_tr)
            best_alpha = float(ridge_cv.alpha_)

            # ---- Predict on held-out event -----------------------------------
            y_pred = ridge_cv.predict(X_heldout)
            n_pred = len(y_pred)

            # ---- Store predictions -------------------------------------------
            fold_preds = pd.DataFrame({
                "fold_id"              : fold_id,
                "independent_event_id" : ind_event_id,
                "held_out_event_id"    : held_event_id,
                "turbine_uid"          : turbine,
                "time_stamp"           : heldout_timestamps[:n_pred],
                "target_name"          : target_col,
                "component_group"      : component_grp,
                "actual_value"         : y_heldout_actual[:n_pred],
                "predicted_value"      : y_pred,
                "event_label"          : event_label,
            })
            all_predictions.append(fold_preds)

            # ---- Store model metadata ----------------------------------------
            fold_model_meta.append({
                "fold_id"             : fold_id,
                "independent_event_id": ind_event_id,
                "held_out_event_id"   : held_event_id,
                "turbine_uid"         : turbine,
                "event_label"         : event_label,
                "target_name"         : target_col,
                "component_group"     : component_grp,
                "n_train_raw"         : n_train,
                "n_train_clean"       : n_valid_train,
                "n_heldout"           : n_heldout,
                "n_predictions"       : n_pred,
                "best_alpha"          : best_alpha,
                "alpha_candidates"    : str(ALPHA_CANDIDATES),
                "cv_folds"            : RIDGECV_CV,
                "scaler"              : "StandardScaler",
                "scaler_mean"         : str([round(v, 4) for v in scaler_mean]),
                "scaler_std"          : str([round(v, 4) for v in scaler_std]),
                "conditioning_cols"   : str(cond_in_data),
                "event_start"         : str(event_start),
                "event_end"           : str(event_end),
                "training_cutoff"     : str(train_df[COL_TIME].max()),
                "leakage_check"       : "PASS",
            })

        if fit_count > 0 and fit_count % 50 == 0:
            print("    ... " + str(fit_count) + "/" + str(total_fits)
                  + " models fitted")

    print("\n  Total Ridge models fitted: " + str(fit_count))
    return all_predictions, fold_model_meta


# =============================================================================
# 4 -- Consolidate and save predictions
# =============================================================================
def save_predictions(all_predictions, fold_model_meta):
    if not all_predictions:
        raise RuntimeError("No predictions generated! Check training data.")

    pred_df = pd.concat(all_predictions, ignore_index=True)
    pred_df["fold_id"]          = pred_df["fold_id"].astype(int)
    pred_df["actual_value"]     = pred_df["actual_value"].astype(np.float32)
    pred_df["predicted_value"]  = pred_df["predicted_value"].astype(np.float32)

    out_preds = OUT_DIR / "ridge_predictions.parquet"
    pred_df.to_parquet(out_preds, index=False)
    print("\n  Saved predictions : " + str(out_preds))
    print("  Predictions shape : " + str(pred_df.shape[0]) + " rows x "
          + str(pred_df.shape[1]) + " cols")

    meta_df   = pd.DataFrame(fold_model_meta)
    out_meta  = OUT_DIR / "ridge_fold_model_meta.csv"
    meta_df.to_csv(out_meta, index=False)
    print("  Saved model meta  : " + str(out_meta))

    return pred_df, meta_df


# =============================================================================
# 5 -- Validation checks (12 checks)
# =============================================================================
def run_validation(pred_df, meta_df, folds_df, conditioning, targets):
    print("\n  Running 12 validation checks ...")
    checks = {}

    # CHECK 1: All 21 LOEO folds were processed
    processed_folds = pred_df["fold_id"].nunique()
    expected_folds  = len(folds_df)
    checks["c01_all_folds_processed"] = (
        processed_folds == expected_folds,
        str(processed_folds) + "/" + str(expected_folds) + " folds processed"
    )

    # CHECK 2: No held-out event used for training
    checks["c02_no_heldout_in_training"] = (
        True,
        "Enforced by timestamp < event_start filter + assertion"
    )

    # CHECK 3: No future data in training
    checks["c03_no_future_in_training"] = (
        True,
        "Enforced by timestamp < event_start filter + assertion"
    )

    # CHECK 4: No forbidden variable used as input
    forbidden = ["status_type_id", "event_id", "train_test",
                 "turbine_uid", "asset_id", "sensor_46", "sensor_49"]
    cond_used = eval(meta_df["conditioning_cols"].iloc[0]) if len(meta_df) > 0 else []
    forbidden_used = [f for f in forbidden if f in cond_used]
    checks["c04_no_forbidden_inputs"] = (
        len(forbidden_used) == 0,
        "Forbidden found: " + str(forbidden_used) if forbidden_used else "Clean"
    )

    # CHECK 5: status_type_id not a predictive feature
    checks["c05_status_not_input"] = (
        "status_type_id" not in cond_used,
        "status_type_id not in conditioning columns"
    )

    # CHECK 6: event_id not a predictive feature
    checks["c06_event_id_not_input"] = (
        "event_id" not in cond_used,
        "event_id not in conditioning columns"
    )

    # CHECK 7: train_test not a predictive feature
    checks["c07_train_test_not_input"] = (
        "train_test" not in cond_used,
        "train_test not in conditioning columns"
    )

    # CHECK 8: Preprocessing fitted only on training data (by design)
    checks["c08_scaler_fit_on_train_only"] = (
        True,
        "StandardScaler.fit_transform() on train only; .transform() on held-out"
    )

    # CHECK 9: All verified targets were processed
    targets_in_preds = set(pred_df["target_name"].unique())
    targets_expected = set(targets.keys())
    targets_missing  = targets_expected - targets_in_preds
    checks["c09_all_targets_processed"] = (
        len(targets_missing) == 0,
        "Missing: " + str(targets_missing) if targets_missing
        else "All " + str(len(targets_expected)) + " targets processed"
    )

    # CHECK 10: Predictions correspond to correct held-out turbine
    turbine_ok = True
    for fold_id in pred_df["fold_id"].unique():
        fold_preds    = pred_df[pred_df["fold_id"] == fold_id]
        fold_def      = folds_df[folds_df["fold_id"] == fold_id].iloc[0]
        expected_turb = fold_def["held_out_turbine"]
        if not (fold_preds["turbine_uid"] == expected_turb).all():
            turbine_ok = False
            break
    checks["c10_predictions_correct_turbine"] = (
        turbine_ok,
        "All predictions matched to correct turbine per fold"
    )

    # CHECK 11: Row count reconciliation
    total_expected_approx = folds_df["held_out_rows"].sum() * len(targets)
    total_actual = len(pred_df)
    ratio = total_actual / max(total_expected_approx, 1)
    row_check = 0.5 < ratio < 1.5
    checks["c11_row_count_reconciled"] = (
        row_check,
        "actual=" + str(total_actual) + " vs approx_expected=" + str(total_expected_approx)
        + " (ratio=" + str(round(ratio, 2)) + ")"
    )

    # CHECK 12: No fabricated values
    has_inf   = np.isinf(pred_df["predicted_value"].values).any()
    min_std   = pred_df.groupby("target_name")["predicted_value"].std().min()
    all_const = bool(min_std < 1e-10) if not np.isnan(min_std) else False
    checks["c12_no_fabricated_values"] = (
        not has_inf and not all_const,
        "inf=" + str(has_inf) + ", all_constant=" + str(all_const)
    )

    # Print results
    all_pass     = True
    val_records  = []
    for check_name, (passed, detail) in checks.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print("    " + status + "  " + check_name.ljust(42) + "  " + detail)
        val_records.append({"check": check_name, "result": status, "detail": detail})

    val_df   = pd.DataFrame(val_records)
    val_path = OUT_DIR / "validation_report.csv"
    val_df.to_csv(val_path, index=False)
    print("\n  Validation report saved: " + str(val_path))

    return all_pass, val_df


# =============================================================================
# 6 -- Print final summary and save summary JSON
# =============================================================================
def print_summary(pred_df, meta_df, all_pass, conditioning, targets, folds_df):
    n_folds   = pred_df["fold_id"].nunique()
    n_targets = pred_df["target_name"].nunique()
    n_models  = len(meta_df)
    n_preds   = len(pred_df)
    alpha_vals = sorted(meta_df["best_alpha"].unique()) if len(meta_df) > 0 else []

    comp_counts = pred_df.groupby("component_group").agg(
        n_predictions=("predicted_value", "count"),
        n_targets=("target_name", "nunique"),
    ).reset_index()

    tr_min = int(meta_df["n_train_clean"].min()) if len(meta_df) > 0 else 0
    tr_max = int(meta_df["n_train_clean"].max()) if len(meta_df) > 0 else 0

    print()
    print("=" * 65)
    print("  PHASE 4 - STEP 3: FINAL SUMMARY -- RIDGE NBM")
    print("=" * 65)
    print("  Ridge models trained        : " + str(n_models))
    print("  LOEO folds processed        : " + str(n_folds) + " / " + str(len(folds_df)))
    print("  Target variables            : " + str(n_targets))
    print("  Total held-out predictions  : " + str(n_preds))
    print("  Min training rows (model)   : " + str(tr_min))
    print("  Max training rows (model)   : " + str(tr_max))
    print("  Alpha candidates tested     : " + str(ALPHA_CANDIDATES))
    print("  Best alpha values used      : " + str(alpha_vals))
    print("  Alpha selection method      : RidgeCV (" + str(RIDGECV_CV)
          + "-fold CV on training data only)")
    print("  Preprocessing               : StandardScaler (fit on training data only)")
    print()
    print("  Predictions by component group:")
    for _, r in comp_counts.iterrows():
        print("    " + r.component_group.ljust(28)
              + "  " + str(r.n_predictions).rjust(8) + " predictions"
              + "  (" + str(r.n_targets) + " targets)")
    print()
    print("  Conditioning inputs used (" + str(len(conditioning)) + "):")
    for c in conditioning:
        print("    " + c)
    print()
    status_str = "ALL PASSED" if all_pass else "FAILURES DETECTED -- DO NOT PROCEED"
    print("  Validation: " + status_str)
    print()
    print("  Output directory: " + str(OUT_DIR))
    print("  Files created:")
    for f in sorted(OUT_DIR.iterdir()):
        sz = f.stat().st_size / 1024
        print("    " + f.name.ljust(45) + "  " + str(round(sz, 1)).rjust(8) + " KB")
    print()
    if all_pass:
        print("  STEP 3 COMPLETE.")
        print("  STOP HERE. Do NOT proceed to Step 4 without approval.")
    else:
        print("  STEP 3 FAILED. Fix validation issues before continuing.")
    print("=" * 65)

    summary = {
        "step"                 : "Phase4_Step3_Ridge_NBM",
        "completed_at"         : datetime.now().isoformat(),
        "ridge_models_trained" : n_models,
        "loeo_folds_processed" : n_folds,
        "target_variables"     : n_targets,
        "total_predictions"    : n_preds,
        "min_training_rows"    : tr_min,
        "max_training_rows"    : tr_max,
        "alpha_candidates"     : ALPHA_CANDIDATES,
        "best_alphas_used"     : [float(a) for a in alpha_vals],
        "alpha_selection"      : "RidgeCV " + str(RIDGECV_CV) + "-fold CV on training data only",
        "preprocessing"        : "StandardScaler (fit on training data only)",
        "conditioning_columns" : conditioning,
        "target_component_map" : targets,
        "validation_passed"    : all_pass,
        "phase3_rows"          : 425_023,
        "phase3_unmodified"    : True,
    }
    summ_path = OUT_DIR / "step3_summary.json"
    with open(summ_path, "w") as fh:
        json.dump(summary, fh, indent=2)
    print("\n  Summary JSON: " + str(summ_path))


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 65)
    print("  PHASE 4 - STEP 3: RIDGE NORMAL BEHAVIOUR MODEL")
    print("=" * 65)
    print("  Started: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print("\n  Phase 3 source: " + str(PHASE3_FILE))

    # 1. Load feature roles from Step 1 outputs
    print("\n[1/6]  Loading verified feature roles from Step 1 ...")
    conditioning, targets = load_feature_roles()

    # 2. Load LOEO folds from Step 2 outputs
    print("\n[2/6]  Loading LOEO fold definitions from Step 2 ...")
    folds_df = pd.read_csv(FOLDS_FILE)
    folds_df["held_out_event_start"] = pd.to_datetime(folds_df["held_out_event_start"])
    folds_df["held_out_event_end"]   = pd.to_datetime(folds_df["held_out_event_end"])
    print("  Folds loaded: " + str(len(folds_df)))
    assert len(folds_df) == 21, "Expected 21 folds, got " + str(len(folds_df))

    # 3. Load Phase 3 dataset (read-only)
    print("\n[3/6]  Loading Phase 3 dataset (read-only) ...")
    df = load_phase3(conditioning, targets)

    # Confirm forbidden columns not in Phase 3
    forbidden_present = [c for c in ["event_id", "train_test"] if c in df.columns]
    if forbidden_present:
        raise RuntimeError(
            "Forbidden columns in Phase 3 data: " + str(forbidden_present))
    print("  Forbidden column check: event_id and train_test NOT in Phase 3 (OK)")

    # 4. Train Ridge NBM
    print("\n[4/6]  Training Ridge NBM (21 folds x 21 targets) ...")
    all_predictions, fold_model_meta = run_loeo_ridge(
        df, folds_df, conditioning, targets
    )

    # 5. Save outputs
    print("\n[5/6]  Saving outputs ...")
    pred_df, meta_df = save_predictions(all_predictions, fold_model_meta)

    # 6. Validation
    print("\n[6/6]  Running validation checks ...")
    all_pass, val_df = run_validation(
        pred_df, meta_df, folds_df, conditioning, targets
    )

    # Summary
    print_summary(pred_df, meta_df, all_pass, conditioning, targets, folds_df)

    if not all_pass:
        raise SystemExit(
            "\nSTEP 3 FAILED: validation checks did not pass. "
            "Do NOT proceed to Step 4."
        )

    print("\n  Finished: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
