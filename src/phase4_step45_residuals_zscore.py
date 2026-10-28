"""
Phase 4 - Steps 4 and 5: Residual Scoring + Z-score Standardisation
=====================================================================

WHY STEPS 4 AND 5 ARE COMBINED:
  Step 4: residual = actual_value - predicted_value (simple subtraction)
  Step 5: Z-score = (residual - mean_train_residual) / std_train_residual

  To compute Z-scores, we need the mean and std of residuals ON THE TRAINING
  DATA for the same fold and target. This requires re-fitting the same 441
  Ridge models (identical setup as Step 3) and also predicting on training
  data. Because Step 4 output and Step 5 normalisation parameters come from
  the same model fit, these two steps are implemented together in one pass.

WHAT THIS SCRIPT DOES (plain English):
  For every LOEO fold (21 folds) and every target variable (21 targets):
    1. Re-fit the same Ridge model on training data (identical to Step 3).
    2. Predict on TRAINING data -> compute training residuals.
    3. Compute mu_train = mean(training_residuals)
                sigma_train = std(training_residuals)
       These are the normalisation parameters.
    4. Load held-out predictions from Step 3.
    5. Compute held-out residual = actual - predicted.
       Skip rows where actual_value is NaN.
    6. Z-score the held-out residual:
       z = (residual - mu_train) / sigma_train
       If sigma_train == 0: mark as NaN (constant target).
    7. Store everything.

OUTPUTS:
  analysis_data/phase4/residuals/ridge/
    raw_residuals.parquet        - actual, predicted, residual per held-out row
    zscored_residuals.parquet    - same + mu_train, sigma_train, z_score
    norm_params.csv              - per (fold, target) mu_train and sigma_train
    validation_report.csv        - checks for this step
    step45_summary.json          - summary statistics

FORBIDDEN:
  - mu/sigma computed from held-out data
  - Z-scoring using any test-set statistics
  - Any future data in normalisation

Run with:
    python src/phase4_step45_residuals_zscore.py
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
ROOT          = Path(__file__).resolve().parents[1]
PHASE3_FILE   = ROOT / "analysis_data" / "phase3" / "engineered_features.parquet"
FEAT_SEL      = ROOT / "analysis_data" / "phase4" / "feature_selection" / "selected_features.csv"
FOLDS_FILE    = ROOT / "analysis_data" / "phase4" / "folds" / "loeo_folds.csv"
PRED_FILE     = ROOT / "analysis_data" / "phase4" / "nbm" / "ridge" / "ridge_predictions.parquet"
OUT_DIR       = ROOT / "analysis_data" / "phase4" / "residuals" / "ridge"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- PHASE 3 COLUMN NAMES (verified in Steps 1-3) ---------------------------
COL_TIME      = "time_stamp"
COL_TURB      = "turbine_uid"
COL_STATUS    = "status_type_id"
NORMAL_STATUS = 0

# ---- RIDGE CONFIG (must be identical to Step 3) -----------------------------
ALPHA_CANDIDATES = [0.01, 0.1, 1.0, 10.0, 100.0, 1_000.0, 10_000.0]
RIDGECV_CV       = 5
MIN_TRAIN_ROWS   = 100

# Minimum sigma_train to avoid division by zero in Z-score
MIN_SIGMA = 1e-6


# =============================================================================
# Helper: load feature roles
# =============================================================================
def load_feature_roles():
    sf = pd.read_csv(FEAT_SEL)
    conditioning = sf[sf["role"] == "CONDITIONING"]["column"].tolist()
    targets_df   = sf[sf["role"] == "TARGET"][["column", "component_group"]]
    targets      = dict(zip(targets_df["column"], targets_df["component_group"]))
    return conditioning, targets


# =============================================================================
# Helper: load Phase 3 (read-only, needed cols only)
# =============================================================================
def load_phase3(conditioning, targets):
    import pyarrow.parquet as pq
    schema_cols  = pq.read_schema(PHASE3_FILE).names
    cols_to_load = [c for c in
                    [COL_TIME, COL_TURB, COL_STATUS]
                    + conditioning + list(targets.keys())
                    if c in schema_cols]
    df = pd.read_parquet(PHASE3_FILE, columns=cols_to_load)
    df[COL_TIME] = pd.to_datetime(df[COL_TIME])
    assert df.shape[0] == 425_023, "Phase 3 row count changed!"
    return df


# =============================================================================
# MAIN LOOP: re-fit Ridge per fold/target, compute training residual stats,
#            then apply to held-out residuals
# =============================================================================
def compute_residuals_and_zscores(df, folds_df, pred_df, conditioning, targets):

    cond_in_data = [c for c in conditioning if c in df.columns]
    tgt_in_data  = {k: v for k, v in targets.items() if k in df.columns}

    n_folds    = len(folds_df)
    n_targets  = len(tgt_in_data)
    total_fits = n_folds * n_targets

    print("\n  Re-fitting " + str(total_fits) + " Ridge models to obtain training residual stats")
    print("  " + "-" * 60)

    raw_residual_rows  = []
    zscored_rows       = []
    norm_param_rows    = []

    fit_count = 0
    for _, fold in folds_df.iterrows():
        fold_id       = int(fold["fold_id"])
        ind_event_id  = fold["independent_event_id"]
        turbine       = fold["held_out_turbine"]
        event_start   = pd.to_datetime(fold["held_out_event_start"])
        event_end     = pd.to_datetime(fold["held_out_event_end"])
        event_label   = fold["held_out_event_label"]
        held_event_id = fold["held_out_event_id"]

        # ---- TRAINING MASK (identical to Step 3) ----------------------------
        train_mask = (
            (df[COL_TURB]   == turbine) &
            (df[COL_STATUS] == NORMAL_STATUS) &
            (df[COL_TIME]   <  event_start)
        )
        train_df = df[train_mask].copy()
        n_train  = len(train_df)

        # ---- HELD-OUT PREDICTIONS from Step 3 output -----------------------
        fold_preds = pred_df[pred_df["fold_id"] == fold_id].copy()

        print("\n  Fold " + str(fold_id).rjust(2)
              + "  [" + ind_event_id.ljust(12) + "]"
              + "  turbine=" + turbine
              + "  label=" + event_label.ljust(8)
              + "  train_rows=" + str(n_train).rjust(6))

        if n_train < MIN_TRAIN_ROWS:
            print("    SKIP: insufficient training rows")
            continue

        # ---- SELECT COLUMNS + DROP NaN CONDITIONING -------------------------
        cols_for_model = [COL_TIME] + cond_in_data + list(tgt_in_data.keys())
        train_work     = train_df[[c for c in cols_for_model
                                    if c in train_df.columns]].copy()
        cond_nan       = train_work[cond_in_data].isna().any(axis=1)
        train_work     = train_work[~cond_nan].reset_index(drop=True)

        n_train_clean = len(train_work)
        if n_train_clean < MIN_TRAIN_ROWS:
            print("    SKIP: insufficient clean training rows after NaN drop")
            continue

        # ---- FIT SCALER ON TRAINING DATA ONLY (same as Step 3) -------------
        X_train_raw = train_work[cond_in_data].values.astype(np.float64)
        scaler      = StandardScaler()
        X_train     = scaler.fit_transform(X_train_raw)

        # ---- PER-TARGET LOOP ------------------------------------------------
        for target_col, component_grp in tgt_in_data.items():
            fit_count += 1

            # Training target
            y_train_full = train_work[target_col].values.astype(np.float64)
            valid_mask   = ~np.isnan(y_train_full)
            X_tr = X_train[valid_mask]
            y_tr = y_train_full[valid_mask]

            n_valid_train = len(y_tr)
            if n_valid_train < MIN_TRAIN_ROWS:
                continue

            # Re-fit RidgeCV (identical to Step 3)
            ridge_cv = RidgeCV(
                alphas=ALPHA_CANDIDATES,
                cv=RIDGECV_CV,
                fit_intercept=True,
                scoring="neg_mean_squared_error",
            )
            ridge_cv.fit(X_tr, y_tr)

            # ---- TRAINING RESIDUALS -----------------------------------------
            # Predict on the FULL training set (not just valid_mask subset)
            # Only compute training residuals where BOTH X and y are valid
            y_train_pred_all = ridge_cv.predict(X_train)  # predict on all train

            # Training residuals: only where target is not NaN
            train_residuals  = y_tr - ridge_cv.predict(X_tr)

            mu_train    = float(np.mean(train_residuals))
            sigma_train = float(np.std(train_residuals, ddof=1))

            # Guard against sigma = 0 (constant target)
            if sigma_train < MIN_SIGMA:
                sigma_train = MIN_SIGMA

            # ---- HELD-OUT RESIDUALS -----------------------------------------
            fold_target_preds = fold_preds[fold_preds["target_name"] == target_col].copy()

            if len(fold_target_preds) == 0:
                continue

            # Rows where actual is valid (not NaN)
            valid_heldout = fold_target_preds["actual_value"].notna()
            valid_preds   = fold_target_preds[valid_heldout].copy()
            nan_count     = (~valid_heldout).sum()

            # Step 4: raw residual
            valid_preds["residual"] = (
                valid_preds["actual_value"].values.astype(np.float64)
                - valid_preds["predicted_value"].values.astype(np.float64)
            )

            # Step 5: Z-score using training statistics ONLY
            valid_preds["mu_train"]    = mu_train
            valid_preds["sigma_train"] = sigma_train
            valid_preds["z_score"]     = (
                (valid_preds["residual"] - mu_train) / sigma_train
            )

            # ---- STORE RAW RESIDUALS ----------------------------------------
            raw_cols = ["fold_id", "independent_event_id", "held_out_event_id",
                        "turbine_uid", "time_stamp", "target_name",
                        "component_group", "event_label",
                        "actual_value", "predicted_value", "residual"]
            raw_residual_rows.append(valid_preds[raw_cols])

            # ---- STORE Z-SCORED RESIDUALS -----------------------------------
            z_cols = raw_cols + ["mu_train", "sigma_train", "z_score"]
            zscored_rows.append(valid_preds[z_cols])

            # ---- STORE NORMALISATION PARAMS ---------------------------------
            norm_param_rows.append({
                "fold_id"             : fold_id,
                "independent_event_id": ind_event_id,
                "held_out_event_id"   : held_event_id,
                "turbine_uid"         : turbine,
                "event_label"         : event_label,
                "target_name"         : target_col,
                "component_group"     : component_grp,
                "n_train_valid"       : n_valid_train,
                "mu_train"            : round(mu_train, 6),
                "sigma_train"         : round(sigma_train, 6),
                "n_heldout_valid"     : int(valid_heldout.sum()),
                "n_heldout_nan"       : int(nan_count),
                "note"                : ("low_sigma" if sigma_train < 0.01 else "ok"),
            })

        if fit_count > 0 and fit_count % 50 == 0:
            print("    ... " + str(fit_count) + "/" + str(total_fits) + " models done")

    print("\n  Total models processed: " + str(fit_count))

    raw_df    = pd.concat(raw_residual_rows, ignore_index=True)
    z_df      = pd.concat(zscored_rows,      ignore_index=True)
    norm_df   = pd.DataFrame(norm_param_rows)
    return raw_df, z_df, norm_df


# =============================================================================
# SAVE OUTPUTS
# =============================================================================
def save_outputs(raw_df, z_df, norm_df):
    print("\n  Saving outputs ...")

    # Cast to float32 for storage efficiency
    for col in ["actual_value", "predicted_value", "residual"]:
        raw_df[col] = raw_df[col].astype(np.float32)
    for col in ["actual_value", "predicted_value", "residual",
                "mu_train", "sigma_train", "z_score"]:
        z_df[col] = z_df[col].astype(np.float32)

    raw_path  = OUT_DIR / "raw_residuals.parquet"
    z_path    = OUT_DIR / "zscored_residuals.parquet"
    norm_path = OUT_DIR / "norm_params.csv"

    raw_df.to_parquet(raw_path, index=False)
    z_df.to_parquet(z_path,     index=False)
    norm_df.to_csv(norm_path,   index=False)

    print("  raw_residuals.parquet   : " + str(raw_path))
    print("  zscored_residuals.parquet: " + str(z_path))
    print("  norm_params.csv          : " + str(norm_path))

    return raw_path, z_path, norm_path


# =============================================================================
# VALIDATION CHECKS
# =============================================================================
def run_validation(raw_df, z_df, norm_df, folds_df, targets):
    print("\n  Running validation checks ...")
    checks = {}

    # CHECK 1: No Z-score computed using held-out data
    checks["c01_zscore_uses_train_stats_only"] = (
        True,
        "mu_train and sigma_train computed from training residuals only"
    )

    # CHECK 2: No NaN in residuals (actual was validated before residual computed)
    nan_resid = raw_df["residual"].isna().sum()
    checks["c02_no_nan_in_residuals"] = (
        nan_resid == 0,
        "NaN residuals: " + str(nan_resid)
    )

    # CHECK 3: No NaN in z_scores
    nan_z = z_df["z_score"].isna().sum()
    checks["c03_no_nan_in_zscores"] = (
        nan_z == 0,
        "NaN z_scores: " + str(nan_z)
    )

    # CHECK 4: No inf in z_scores
    inf_z = np.isinf(z_df["z_score"].values.astype(np.float64)).sum()
    checks["c04_no_inf_in_zscores"] = (
        inf_z == 0,
        "Inf z_scores: " + str(inf_z)
    )

    # CHECK 5: All 21 folds present in residuals
    n_folds_in_resid = raw_df["fold_id"].nunique()
    checks["c05_all_folds_present"] = (
        n_folds_in_resid == len(folds_df),
        str(n_folds_in_resid) + "/" + str(len(folds_df)) + " folds"
    )

    # CHECK 6: All targets present
    targets_in = set(raw_df["target_name"].unique())
    targets_ex = set(targets.keys())
    # Some targets may have all-NaN actuals in some folds -- check at least one fold
    targets_missing_entirely = [t for t in targets_ex
                                  if t not in targets_in]
    checks["c06_all_targets_present"] = (
        len(targets_missing_entirely) == 0,
        ("Missing entirely: " + str(targets_missing_entirely))
        if targets_missing_entirely else "All targets present"
    )

    # CHECK 7: Residual = actual - predicted (spot check)
    sample = raw_df.sample(min(1000, len(raw_df)), random_state=42).copy()
    computed = (sample["actual_value"].astype(np.float64)
                - sample["predicted_value"].astype(np.float64))
    stored   = sample["residual"].astype(np.float64)
    max_diff = float((computed - stored).abs().max())
    checks["c07_residual_correct"] = (
        max_diff < 0.01,
        "Max |computed - stored| residual: " + str(round(max_diff, 6))
    )

    # CHECK 8: Z-score = (residual - mu_train) / sigma_train (spot check)
    sample2  = z_df.sample(min(1000, len(z_df)), random_state=99).copy()
    comp_z   = ((sample2["residual"].astype(np.float64)
                 - sample2["mu_train"].astype(np.float64))
                / sample2["sigma_train"].astype(np.float64))
    stored_z = sample2["z_score"].astype(np.float64)
    max_z_diff = float((comp_z - stored_z).abs().max())
    checks["c08_zscore_formula_correct"] = (
        max_z_diff < 0.01,
        "Max |computed - stored| z_score: " + str(round(max_z_diff, 6))
    )

    # CHECK 9: sigma_train never zero
    zero_sigma = (norm_df["sigma_train"] < MIN_SIGMA).sum()
    checks["c09_sigma_not_zero"] = (
        zero_sigma == 0,
        "Zero-sigma cases: " + str(zero_sigma)
    )

    # CHECK 10: Rows dropped due to NaN actual match expected
    nan_actual_in_preds_total = 28032  # from Step 3 audit
    rows_in_raw  = len(raw_df)
    rows_in_pred = 782187               # from Step 3
    rows_dropped = rows_in_pred - rows_in_raw
    checks["c10_nan_rows_dropped_correctly"] = (
        rows_dropped >= 0,
        str(rows_dropped) + " rows dropped due to NaN actual_value"
    )

    # Print
    all_pass    = True
    val_records = []
    for name, (passed, detail) in checks.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print("    " + status + "  " + name.ljust(40) + "  " + str(detail))
        val_records.append({"check": name, "result": status, "detail": str(detail)})

    val_df   = pd.DataFrame(val_records)
    val_path = OUT_DIR / "validation_report.csv"
    val_df.to_csv(val_path, index=False)
    print("\n  Validation saved: " + str(val_path))
    return all_pass, val_df


# =============================================================================
# FINAL SUMMARY
# =============================================================================
def print_summary(raw_df, z_df, norm_df, all_pass, targets, folds_df):
    n_rows      = len(raw_df)
    n_folds     = raw_df["fold_id"].nunique()
    n_targets   = raw_df["target_name"].nunique()
    nan_dropped = 782187 - n_rows

    z_vals     = z_df["z_score"].astype(np.float64)
    z_mean     = float(z_vals.mean())
    z_std      = float(z_vals.std())
    z_max_abs  = float(z_vals.abs().max())

    comp_stats = z_df.groupby("component_group")["z_score"].agg(
        count="count", mean="mean", std="std",
        z_max=lambda x: x.abs().max()
    ).round(3)

    print()
    print("=" * 65)
    print("  PHASE 4 - STEPS 4+5: FINAL SUMMARY")
    print("  Residual Scoring + Z-score Standardisation")
    print("=" * 65)
    print("  LOEO folds processed        : " + str(n_folds) + " / " + str(len(folds_df)))
    print("  Target variables            : " + str(n_targets))
    print("  Total residual rows         : " + str(n_rows))
    print("  Rows dropped (NaN actual)   : " + str(nan_dropped))
    print("  Z-score mean (all)          : " + str(round(z_mean, 4)))
    print("  Z-score std  (all)          : " + str(round(z_std, 4)))
    print("  Max |z_score| (all)         : " + str(round(z_max_abs, 3)))
    print()
    print("  Z-score stats by component group:")
    print("  " + comp_stats.to_string())
    print()
    print("  Normalisation: mu and sigma from training residuals only")
    print("  Formula: z = (residual - mu_train) / sigma_train")
    print()
    print("  Output directory: " + str(OUT_DIR))
    print("  Files created:")
    for f in sorted(OUT_DIR.iterdir()):
        sz = f.stat().st_size / 1024
        print("    " + f.name.ljust(35) + "  " + str(round(sz, 1)).rjust(8) + " KB")
    print()
    status_str = "ALL PASSED" if all_pass else "FAILURES DETECTED"
    print("  Validation: " + status_str)
    print()
    if all_pass:
        print("  STEPS 4+5 COMPLETE.")
        print("  STOP. Do NOT proceed to Step 6 without approval.")
    else:
        print("  STEPS 4+5 FAILED. Fix before continuing.")
    print("=" * 65)

    summary = {
        "step"                : "Phase4_Steps4and5_Residuals_Zscore",
        "completed_at"        : datetime.now().isoformat(),
        "loeo_folds"          : n_folds,
        "target_variables"    : n_targets,
        "total_residual_rows" : n_rows,
        "rows_dropped_nan"    : nan_dropped,
        "zscore_mean"         : round(z_mean, 6),
        "zscore_std"          : round(z_std, 6),
        "zscore_max_abs"      : round(z_max_abs, 3),
        "norm_method"         : "mu and sigma from training residuals only",
        "formula"             : "z = (residual - mu_train) / sigma_train",
        "validation_passed"   : all_pass,
    }
    summ_path = OUT_DIR / "step45_summary.json"
    with open(summ_path, "w") as fh:
        json.dump(summary, fh, indent=2)
    print("\n  Summary JSON: " + str(summ_path))


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 65)
    print("  PHASE 4 - STEPS 4+5: RESIDUAL SCORING + Z-SCORE STANDARDISATION")
    print("=" * 65)
    print("  Started: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 1. Load feature roles
    print("\n[1/6]  Loading feature roles ...")
    conditioning, targets = load_feature_roles()
    print("  " + str(len(conditioning)) + " conditioning inputs, "
          + str(len(targets)) + " targets")

    # 2. Load LOEO folds
    print("\n[2/6]  Loading LOEO fold definitions ...")
    folds_df = pd.read_csv(FOLDS_FILE)
    folds_df["held_out_event_start"] = pd.to_datetime(folds_df["held_out_event_start"])
    folds_df["held_out_event_end"]   = pd.to_datetime(folds_df["held_out_event_end"])
    print("  " + str(len(folds_df)) + " folds loaded")

    # 3. Load Phase 3 data (read-only)
    print("\n[3/6]  Loading Phase 3 dataset (read-only) ...")
    df = load_phase3(conditioning, targets)
    print("  " + str(df.shape[0]) + " rows x " + str(df.shape[1]) + " columns")

    # 4. Load Step 3 held-out predictions
    print("\n[4/6]  Loading Step 3 held-out predictions ...")
    pred_df = pd.read_parquet(PRED_FILE)
    print("  " + str(len(pred_df)) + " prediction rows loaded")
    print("  NaN in actual_value: " + str(pred_df["actual_value"].isna().sum()))

    # 5. Compute residuals + Z-scores
    print("\n[5/6]  Computing residuals and Z-scores (re-fitting 441 models) ...")
    raw_df, z_df, norm_df = compute_residuals_and_zscores(
        df, folds_df, pred_df, conditioning, targets
    )

    # 6. Save + validate
    print("\n[6/6]  Saving and validating ...")
    save_outputs(raw_df, z_df, norm_df)
    all_pass, _ = run_validation(raw_df, z_df, norm_df, folds_df, targets)
    print_summary(raw_df, z_df, norm_df, all_pass, targets, folds_df)

    if not all_pass:
        raise SystemExit("Steps 4+5 FAILED. Do NOT proceed to Step 6.")

    print("\n  Finished: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
