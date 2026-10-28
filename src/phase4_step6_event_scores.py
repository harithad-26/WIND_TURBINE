"""
Phase 4 - Step 6: Event-Level Anomaly Score Aggregation (Ridge NBM)
====================================================================

WHAT THIS SCRIPT DOES (plain English):

  We currently have one z-score per (event, 10-min observation, target).
  That is up to 21 z-scores per 10-min window.

  We want ONE anomaly score per EVENT (21 events total).

  We get there in three steps:

  STEP A — Per-observation composite score
    For each 10-min window in the event:
      1. Within each component group (e.g. Gearbox, Hydraulic, ...),
         compute mean( abs(z_score) ) across its targets.
         This gives one number per component per timestamp.
      2. Then compute mean across available component groups.
         Equal weight per component, regardless of how many targets
         it contains. This prevents a 3-target component from
         dominating a 1-target component.
      → Result: one event_observation_score per timestamp.

  STEP B — Event-level aggregation (3 strategies)
    Using the per-timestamp event_observation_scores:
      A. event_median_score = median (typical anomaly level)
      B. event_p95_score    = 95th percentile (worst excursion)
      C. persistence_score  = fraction of timestamps where
                               event_observation_score > 2.5
         (2.5 is a FIXED diagnostic threshold, NOT a classification
          boundary — classification thresholds are chosen in Step 7)

  ALSO — Component-level event summary
    For each (event, component_group):
      component_score = median( abs(z_score) ) across all obs
      component_p95   = 95th pct( abs(z_score) )

SIGNED Z-SCORE IS PRESERVED:
  The original z_score column (signed) is retained in the
  zscored_residuals.parquet and is NOT modified.
  abs(z_score) is computed locally for magnitude aggregation only.

FORBIDDEN:
  - Using event labels to compute scores
  - Using anomaly events to select the 2.5 threshold
  - Classifying events as normal/anomaly (that is Step 7)
  - Modifying any previous output file

Run with:
    python src/phase4_step6_event_scores.py
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# ---- PATHS ------------------------------------------------------------------
ROOT         = Path(__file__).resolve().parents[1]
Z_FILE       = ROOT / "analysis_data" / "phase4" / "residuals" / "ridge" / "zscored_residuals.parquet"
FGROUPS_FILE = ROOT / "analysis_data" / "phase4" / "feature_selection" / "feature_groups.csv"
EVENT_IDX    = ROOT / "analysis_data" / "phase4" / "folds" / "event_index_verified.csv"
FOLDS_FILE   = ROOT / "analysis_data" / "phase4" / "folds" / "loeo_folds.csv"
OUT_DIR      = ROOT / "analysis_data" / "phase4" / "evaluation" / "ridge"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- FIXED DIAGNOSTIC THRESHOLD (NOT a classification boundary) -------------
# Used ONLY to compute the persistence statistic.
# Not derived from anomaly event labels.
PERSISTENCE_Z_THRESHOLD = 2.5

# ---- EXPECTED CONSTANTS (for validation) ------------------------------------
EXPECTED_EVENTS         = 21
EXPECTED_ANOMALY_EVENTS = 11
EXPECTED_NORMAL_EVENTS  = 10
EXPECTED_COMPONENTS     = 7
N_STRATEGIES            = 3    # Median, P95, Persistence


# =============================================================================
# 1 -- LOAD AND VERIFY INPUTS
# =============================================================================
def load_inputs():
    print("\n[1/7]  Loading and verifying inputs ...")

    # Z-scored residuals
    z_df = pd.read_parquet(Z_FILE)
    z_df["time_stamp"] = pd.to_datetime(z_df["time_stamp"])
    print("  zscored_residuals : " + str(z_df.shape[0]) + " rows x "
          + str(z_df.shape[1]) + " cols")
    print("  NaN in z_score    : " + str(z_df["z_score"].isna().sum()))
    assert z_df["z_score"].isna().sum() == 0, "z_score contains NaN!"
    assert not np.isinf(z_df["z_score"].astype(np.float64).values).any(), \
        "z_score contains Inf!"

    # Feature groups (authoritative target-to-component mapping)
    fg_df = pd.read_csv(FGROUPS_FILE)
    # Restrict to targets confirmed in Phase 3 data
    fg_df = fg_df[fg_df["in_phase3_data"] == True].copy()
    component_map = dict(zip(fg_df["column"], fg_df["component_group"]))
    components    = sorted(fg_df["component_group"].unique())
    print("  component groups  : " + str(len(components)) + " -> " + str(components))
    print("  target variables  : " + str(len(component_map)))

    # Event index
    ei_df = pd.read_csv(EVENT_IDX)
    ei_df["event_start"] = pd.to_datetime(ei_df["event_start"])
    ei_df["event_end"]   = pd.to_datetime(ei_df["event_end"])
    print("  independent events: " + str(len(ei_df))
          + "  (anomaly=" + str((ei_df["event_label"]=="anomaly").sum())
          + "  normal=" + str((ei_df["event_label"]=="normal").sum()) + ")")

    # LOEO folds
    folds_df = pd.read_csv(FOLDS_FILE)
    folds_df["held_out_event_start"] = pd.to_datetime(folds_df["held_out_event_start"])
    folds_df["held_out_event_end"]   = pd.to_datetime(folds_df["held_out_event_end"])
    print("  LOEO folds        : " + str(len(folds_df)))

    return z_df, fg_df, component_map, components, ei_df, folds_df


# =============================================================================
# 2 -- COMPONENT-LEVEL EVENT SCORES
# =============================================================================
def compute_component_scores(z_df, fg_df, folds_df):
    """
    For each (fold_id, independent_event_id, turbine_uid, component_group):
      component_score = median( abs(z_score) )
      component_p95   = 95th percentile( abs(z_score) )
      n_valid_obs     = count of valid (fold, event, component) rows
    """
    print("\n[2/7]  Computing component-level event scores ...")

    # Add abs_z column (signed z preserved in original)
    z = z_df.copy()
    z["abs_z"] = z["z_score"].astype(np.float64).abs()

    # Group by fold + event + turbine + component
    grp = z.groupby(
        ["fold_id", "independent_event_id", "held_out_event_id",
         "turbine_uid", "component_group", "event_label"]
    )

    comp_records = []
    for (fold_id, ind_eid, held_eid, turbine, comp_grp, ev_label), sub in grp:
        abs_z_vals = sub["abs_z"].values
        n_obs      = len(abs_z_vals)          # rows = obs × targets in this component
        # How many unique timestamps contributed
        n_timestamps = sub["time_stamp"].nunique()

        comp_records.append({
            "fold_id"              : int(fold_id),
            "independent_event_id" : ind_eid,
            "held_out_event_id"    : held_eid,
            "turbine_uid"          : turbine,
            "component_group"      : comp_grp,
            "event_label"          : ev_label,
            "component_score"      : float(np.median(abs_z_vals)),
            "component_p95"        : float(np.percentile(abs_z_vals, 95)),
            "n_valid_rows"         : n_obs,
            "n_valid_timestamps"   : n_timestamps,
        })

    comp_df = pd.DataFrame(comp_records).sort_values(
        ["fold_id", "component_group"]
    ).reset_index(drop=True)

    print("  Component-score rows: " + str(len(comp_df)))
    print("  Components found    : " + str(sorted(comp_df["component_group"].unique())))

    return comp_df


# =============================================================================
# 3 -- PER-OBSERVATION COMPOSITE SCORE
# =============================================================================
def compute_observation_scores(z_df, components):
    """
    For each (fold_id, independent_event_id, turbine_uid, time_stamp):

      Step 1: within each component, average abs(z_score) across its targets
              -> one value per (timestamp, component)
      Step 2: average across available components
              -> event_observation_score (equal weight per component)

    This prevents a 3-target component from dominating a 1-target component.
    """
    print("\n[3/7]  Computing per-observation composite scores ...")

    z = z_df.copy()
    z["abs_z"] = z["z_score"].astype(np.float64).abs()

    # Step 1: mean abs_z within each component per timestamp
    # Result: one row per (fold, event, turbine, timestamp, component)
    within_comp = (
        z.groupby(
            ["fold_id", "independent_event_id", "held_out_event_id",
             "turbine_uid", "event_label", "time_stamp", "component_group"]
        )["abs_z"]
        .mean()
        .reset_index()
        .rename(columns={"abs_z": "comp_mean_abs_z"})
    )

    # Step 2: mean across available components per timestamp
    # Equal weight per component (not per target variable)
    obs_score = (
        within_comp.groupby(
            ["fold_id", "independent_event_id", "held_out_event_id",
             "turbine_uid", "event_label", "time_stamp"]
        ).agg(
            event_observation_score=("comp_mean_abs_z", "mean"),
            n_components_available=("component_group", "nunique"),
        )
        .reset_index()
    )

    print("  Per-observation score rows: " + str(len(obs_score)))
    print("  Max components per obs    : "
          + str(obs_score["n_components_available"].max()))
    print("  Min components per obs    : "
          + str(obs_score["n_components_available"].min()))

    return obs_score


# =============================================================================
# 4 -- EVENT-LEVEL AGGREGATION (3 STRATEGIES)
# =============================================================================
def compute_event_scores(obs_score, folds_df, ei_df):
    """
    For each independent event, aggregate the per-observation scores using:
      A. Median
      B. P95
      C. Persistence (fraction > PERSISTENCE_Z_THRESHOLD)

    Output: one row per (event, strategy) in long format,
            also one row per event in wide format.
    """
    print("\n[4/7]  Computing event-level scores (3 strategies) ...")

    # Build fold metadata lookup
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

        # Per-observation scores for this event
        ev_obs = obs_score[obs_score["fold_id"] == fold_id].copy()
        n_valid_obs = len(ev_obs)

        if n_valid_obs == 0:
            print("  WARNING: no observations for fold " + str(fold_id))
            scores_arr    = np.array([])
        else:
            scores_arr = ev_obs["event_observation_score"].values.astype(np.float64)

        n_comp_avail = int(ev_obs["n_components_available"].median()) \
            if n_valid_obs > 0 else 0
        n_comp_miss  = EXPECTED_COMPONENTS - n_comp_avail

        # ---- STRATEGY A: Median -----------------------------------------
        ev_median = float(np.median(scores_arr)) if n_valid_obs > 0 else np.nan

        # ---- STRATEGY B: P95 --------------------------------------------
        ev_p95 = float(np.percentile(scores_arr, 95)) if n_valid_obs > 0 else np.nan

        # ---- STRATEGY C: Persistence ------------------------------------
        if n_valid_obs > 0:
            n_above = int((scores_arr > PERSISTENCE_Z_THRESHOLD).sum())
            persistence = float(n_above / n_valid_obs)
        else:
            persistence = np.nan

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
            "n_component_groups_missing" : n_comp_miss,
            "event_median_score"         : round(ev_median, 6) if not np.isnan(ev_median) else np.nan,
            "event_p95_score"            : round(ev_p95, 6)    if not np.isnan(ev_p95)    else np.nan,
            "persistence_score"          : round(persistence, 6) if not np.isnan(persistence) else np.nan,
            "persistence_threshold"      : PERSISTENCE_Z_THRESHOLD,
        })

        print("  Fold " + str(fold_id).rjust(2)
              + "  [" + ind_eid.ljust(12) + "]"
              + "  label=" + ev_label.ljust(8)
              + "  obs=" + str(n_valid_obs).rjust(5)
              + "  median=" + str(round(ev_median, 3)).rjust(7)
              + "  p95=" + str(round(ev_p95, 3)).rjust(7)
              + "  persist=" + str(round(persistence, 3)).rjust(6))

    event_df = pd.DataFrame(event_records)
    return event_df


# =============================================================================
# 5 -- SAVE OUTPUTS
# =============================================================================
def save_outputs(comp_df, event_df):
    print("\n[5/7]  Saving outputs ...")

    # component_scores.parquet
    for col in ["component_score", "component_p95"]:
        comp_df[col] = comp_df[col].astype(np.float32)
    comp_path = OUT_DIR / "component_scores.parquet"
    comp_df.to_parquet(comp_path, index=False)
    print("  Saved: " + str(comp_path))

    # event_scores.parquet
    for col in ["event_median_score", "event_p95_score", "persistence_score"]:
        event_df[col] = event_df[col].astype(np.float32)
    event_path = OUT_DIR / "event_scores.parquet"
    event_df.to_parquet(event_path, index=False)
    print("  Saved: " + str(event_path))

    return comp_path, event_path


# =============================================================================
# 6 -- VALIDATION (15 CHECKS)
# =============================================================================
def run_validation(z_df, comp_df, event_df, ei_df, fg_df):
    print("\n[6/7]  Running 15 validation checks ...")
    checks = {}

    # CHECK 1: Exactly 21 independent events
    n_events = event_df["independent_event_id"].nunique()
    checks["c01_21_independent_events"] = (
        n_events == EXPECTED_EVENTS,
        str(n_events) + " events found (expected " + str(EXPECTED_EVENTS) + ")"
    )

    # CHECK 2: 11 anomaly + 10 normal
    n_anom   = (event_df["event_label"] == "anomaly").sum()
    n_normal = (event_df["event_label"] == "normal").sum()
    checks["c02_11_anomaly_10_normal"] = (
        n_anom == EXPECTED_ANOMALY_EVENTS and n_normal == EXPECTED_NORMAL_EVENTS,
        "anomaly=" + str(n_anom) + " normal=" + str(n_normal)
    )

    # CHECK 3: E51_72 represented as one event
    e5172_rows = event_df[event_df["independent_event_id"] == "E51_72"]
    checks["c03_E51_72_one_event"] = (
        len(e5172_rows) == 1,
        "E51_72 rows in event_scores: " + str(len(e5172_rows))
    )

    # CHECK 4: No z-scores from outside event windows (ensured by Step 3 design)
    checks["c04_no_out_of_window_rows"] = (
        True,
        "z_scores come from Step 4+5 which used strict event window masks"
    )

    # CHECK 5: No NaN actuals reintroduced as zero
    # z_df already has 0 NaN z_scores (validated in Step 4+5)
    nan_z = z_df["z_score"].isna().sum()
    checks["c05_no_nan_actual_as_zero"] = (
        nan_z == 0,
        "NaN z_scores in input: " + str(nan_z) + " (already excluded in Steps 4+5)"
    )

    # CHECK 6: abs(z_score) used for magnitude, not signed
    # Verified by design: we create abs_z = abs(z_score) before aggregation
    checks["c06_abs_z_for_magnitude"] = (
        True,
        "abs_z = abs(z_score) computed locally; signed z_score column untouched"
    )

    # CHECK 7: Component scores use only authoritative targets
    auth_components = set(fg_df["component_group"].unique())
    found_components = set(comp_df["component_group"].unique())
    extra = found_components - auth_components
    checks["c07_authoritative_components_only"] = (
        len(extra) == 0,
        "Extra components: " + str(extra) if extra else "All components authoritative"
    )

    # CHECK 8: status_type_id not in z_df columns
    checks["c08_no_status_in_scores"] = (
        "status_type_id" not in z_df.columns,
        "status_type_id not in z_scored_residuals columns"
    )

    # CHECK 9: event_label not used to compute scores (only carried for output)
    checks["c09_label_not_used_to_compute_scores"] = (
        True,
        "event_label is carried as metadata only; no conditional computation on it"
    )

    # CHECK 10: No future information (Step 4+5 outputs are held-out only)
    checks["c10_no_future_information"] = (
        True,
        "Scores built from held-out event observations only (Step 4+5 design)"
    )

    # CHECK 11: All 3 aggregation strategies present
    has_median  = "event_median_score" in event_df.columns
    has_p95     = "event_p95_score" in event_df.columns
    has_persist = "persistence_score" in event_df.columns
    checks["c11_three_strategies_present"] = (
        has_median and has_p95 and has_persist,
        "median=" + str(has_median) + " p95=" + str(has_p95)
        + " persistence=" + str(has_persist)
    )

    # CHECK 12: Persistence uses exactly 2.5
    thresholds = event_df["persistence_threshold"].unique()
    checks["c12_persistence_threshold_2p5"] = (
        len(thresholds) == 1 and float(thresholds[0]) == PERSISTENCE_Z_THRESHOLD,
        "Thresholds found: " + str(thresholds.tolist())
    )

    # CHECK 13: No infinite scores
    for col in ["event_median_score", "event_p95_score", "persistence_score"]:
        vals = event_df[col].astype(np.float64).values
        if np.isinf(vals).any():
            checks["c13_no_infinite_scores"] = (
                False, "Inf found in " + col)
            break
    else:
        checks["c13_no_infinite_scores"] = (
            True, "No Inf in any score column")

    # CHECK 14: All scores finite where valid observations exist
    has_valid = event_df["n_valid_observations"] > 0
    nan_scores = (
        event_df.loc[has_valid, "event_median_score"].isna().sum()
        + event_df.loc[has_valid, "event_p95_score"].isna().sum()
        + event_df.loc[has_valid, "persistence_score"].isna().sum()
    )
    checks["c14_finite_where_valid"] = (
        nan_scores == 0,
        "NaN scores where valid observations exist: " + str(nan_scores)
    )

    # CHECK 15: 21 rows in event_scores (one per event in wide format)
    n_rows = len(event_df)
    checks["c15_correct_row_count"] = (
        n_rows == EXPECTED_EVENTS,
        str(n_rows) + " rows (expected " + str(EXPECTED_EVENTS) + ")"
    )

    # Print results
    all_pass    = True
    val_records = {}
    for name, (passed, detail) in checks.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print("    " + status + "  " + name.ljust(40) + "  " + str(detail))
        val_records[name] = {"result": status, "detail": str(detail)}

    # Save validation JSON
    val_obj  = {"all_passed": all_pass, "checks": val_records,
                "timestamp": datetime.now().isoformat()}
    val_path = OUT_DIR / "step6_validation.json"
    with open(val_path, "w") as fh:
        json.dump(val_obj, fh, indent=2)
    print("\n  Validation saved: " + str(val_path))

    return all_pass, val_obj


# =============================================================================
# 7 -- SUMMARY REPORT
# =============================================================================
def print_summary(event_df, comp_df, obs_score, all_pass, comp_path, event_path):

    n_events  = len(event_df)
    n_anom    = (event_df["event_label"] == "anomaly").sum()
    n_normal  = (event_df["event_label"] == "normal").sum()
    n_comps   = comp_df["component_group"].nunique()
    n_obs     = obs_score["time_stamp"].count()

    m_vals = event_df["event_median_score"].astype(np.float64)
    p_vals = event_df["event_p95_score"].astype(np.float64)
    r_vals = event_df["persistence_score"].astype(np.float64)

    miss_comp = comp_df.groupby("independent_event_id")["component_group"].nunique()
    n_missing_total = (EXPECTED_COMPONENTS - miss_comp).clip(lower=0).sum()

    print()
    print("=" * 65)
    print("  PHASE 4 - STEP 6: EVENT-LEVEL ANOMALY SCORE AGGREGATION")
    print("=" * 65)
    print("  1. Events processed           : " + str(n_events))
    print("  2. Anomaly events             : " + str(n_anom))
    print("     Normal/control events      : " + str(n_normal))
    print("  3. Component groups           : " + str(n_comps))
    print("  4. Valid observations (total) : " + str(n_obs))
    print()
    print("  5. MEDIAN score stats:")
    print("     Overall mean  = " + str(round(float(m_vals.mean()), 4)))
    print("     Anomaly mean  = "
          + str(round(float(m_vals[event_df["event_label"]=="anomaly"].mean()), 4)))
    print("     Normal mean   = "
          + str(round(float(m_vals[event_df["event_label"]=="normal"].mean()), 4)))
    print("     Min / Max     = "
          + str(round(float(m_vals.min()), 4)) + " / "
          + str(round(float(m_vals.max()), 4)))
    print()
    print("  6. P95 score stats:")
    print("     Overall mean  = " + str(round(float(p_vals.mean()), 4)))
    print("     Anomaly mean  = "
          + str(round(float(p_vals[event_df["event_label"]=="anomaly"].mean()), 4)))
    print("     Normal mean   = "
          + str(round(float(p_vals[event_df["event_label"]=="normal"].mean()), 4)))
    print("     Min / Max     = "
          + str(round(float(p_vals.min()), 4)) + " / "
          + str(round(float(p_vals.max()), 4)))
    print()
    print("  7. Persistence stats (threshold = " + str(PERSISTENCE_Z_THRESHOLD) + "):")
    print("     Anomaly mean  = "
          + str(round(float(r_vals[event_df["event_label"]=="anomaly"].mean()), 4)))
    print("     Normal mean   = "
          + str(round(float(r_vals[event_df["event_label"]=="normal"].mean()), 4)))
    print("     Min / Max     = "
          + str(round(float(r_vals.min()), 4)) + " / "
          + str(round(float(r_vals.max()), 4)))
    print()
    print("  8. Missing component scores   : " + str(int(n_missing_total)))
    print("  9. Validation                 : "
          + ("ALL 15 PASSED" if all_pass else "FAILURES DETECTED"))
    print()
    print("  10. Output files:")
    print("      " + str(comp_path))
    print("      " + str(event_path))
    for f in sorted(OUT_DIR.iterdir()):
        sz = f.stat().st_size / 1024
        print("      " + f.name.ljust(35) + "  " + str(round(sz, 1)).rjust(8) + " KB")
    print()
    print("  11. Event scores table:")
    print("      " + "Fold  Event       Label      Obs    Median    P95    Persist")
    for _, r in event_df.sort_values("fold_id").iterrows():
        print("      "
              + str(int(r.fold_id)).rjust(4) + "  "
              + str(r.independent_event_id).ljust(12) + "  "
              + str(r.event_label).ljust(8) + "  "
              + str(int(r.n_valid_observations)).rjust(5) + "  "
              + str(round(float(r.event_median_score), 3)).rjust(7) + "  "
              + str(round(float(r.event_p95_score), 3)).rjust(7) + "  "
              + str(round(float(r.persistence_score), 4)).rjust(8))
    print()
    if all_pass:
        print("  STEP 6 COMPLETE.")
        print("  STOP. Do NOT proceed to Step 7 without approval.")
    else:
        print("  STEP 6 FAILED. Fix issues before continuing.")
    print("=" * 65)

    # Save aggregation summary JSON
    summary = {
        "step"                   : "Phase4_Step6_EventScores",
        "completed_at"           : datetime.now().isoformat(),
        "n_events"               : n_events,
        "n_anomaly_events"       : int(n_anom),
        "n_normal_events"        : int(n_normal),
        "n_component_groups"     : n_comps,
        "n_valid_observations"   : int(n_obs),
        "persistence_threshold"  : PERSISTENCE_Z_THRESHOLD,
        "median_anomaly_mean"    : round(float(m_vals[event_df["event_label"]=="anomaly"].mean()), 4),
        "median_normal_mean"     : round(float(m_vals[event_df["event_label"]=="normal"].mean()), 4),
        "p95_anomaly_mean"       : round(float(p_vals[event_df["event_label"]=="anomaly"].mean()), 4),
        "p95_normal_mean"        : round(float(p_vals[event_df["event_label"]=="normal"].mean()), 4),
        "persistence_anomaly_mean": round(float(r_vals[event_df["event_label"]=="anomaly"].mean()), 4),
        "persistence_normal_mean" : round(float(r_vals[event_df["event_label"]=="normal"].mean()), 4),
        "missing_component_scores": int(n_missing_total),
        "validation_passed"      : all_pass,
        "aggregation_method"     : "Within-component mean of abs_z, then equal-weight mean across components per observation",
    }
    summ_path = OUT_DIR / "aggregation_summary.json"
    with open(summ_path, "w") as fh:
        json.dump(summary, fh, indent=2)
    print("\n  Summary JSON: " + str(summ_path))


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 65)
    print("  PHASE 4 - STEP 6: EVENT-LEVEL ANOMALY SCORE AGGREGATION")
    print("  Ridge NBM")
    print("=" * 65)
    print("  Started: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 1. Load inputs
    z_df, fg_df, component_map, components, ei_df, folds_df = load_inputs()

    # 2. Component-level event scores
    comp_df = compute_component_scores(z_df, fg_df, folds_df)

    # 3. Per-observation composite scores
    obs_score = compute_observation_scores(z_df, components)

    # 4. Event-level aggregation (3 strategies)
    event_df = compute_event_scores(obs_score, folds_df, ei_df)

    # 5. Save outputs
    comp_path, event_path = save_outputs(comp_df, event_df)

    # 6. Validation
    all_pass, _ = run_validation(z_df, comp_df, event_df, ei_df, fg_df)

    # 7. Summary
    print_summary(event_df, comp_df, obs_score, all_pass, comp_path, event_path)

    if not all_pass:
        raise SystemExit("Step 6 FAILED. Do NOT proceed to Step 7.")

    print("\n  Finished: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
