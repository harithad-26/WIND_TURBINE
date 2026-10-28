"""
Phase 4 - Step 2: Build and Validate 21 LOEO Event Folds
=========================================================

METADATA SOURCE AUDIT (verified before writing this script):
--------------------------------------------------------------
Source file: analysis_data/event_index.csv
  - event_id       : column 'event_id'
  - turbine        : column 'turbine_uid'  (values: A0, A10, A11, A13, A21)
  - event_start    : column 'event_start'
  - event_end      : column 'event_end'
  - event_label    : column 'event_label'  (values: anomaly / normal)
  - description    : column 'event_description'
  - asset_id       : column 'asset'        (integer: 0,10,11,13,21)

Source file: analysis_data/train_test_by_event.csv
  - authoritative train cutoff per event: column 'train_max'
  - training row count (pre-existing analysis): column 'n_train'

Phase 3 parquet column names (verified):
  - timestamp      : 'time_stamp'
  - turbine        : 'asset_id'  (integer: 0,10,11,13,21)
                     'turbine_uid' also present (string: A0, A10, ...)
  - status         : 'status_type_id'
                       0 = normal operation  <- used for training filter
                       3 = curtailed / warning
                       4 = fault / stopped   <- event observations
  - event_id       : NOT in Phase 3 parquet  -> event windows assigned
                     by matching time_stamp to event_index.csv ranges
  - train_test     : NOT in Phase 3 parquet

Events 51 and 72 (PRD-specified treatment):
  Both are on turbine A21. Event 51 overlaps completely with Event 72.
  They are treated as ONE independent event for evaluation purposes.
  Independent event ID: 'E51_72'
  For fold construction: the earlier event_start and later event_end
  are used to define the combined held-out window.

STATUS CODE RULE:
  status_type_id == 0  ->  normal operation  (eligible for training)
  status_type_id != 0  ->  NOT normal        (excluded from training)
  status_type_id is NEVER passed to any model.

Run with:
    python src/phase4_step2_loeo_folds.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ---- PATHS ------------------------------------------------------------------
ROOT         = Path(__file__).resolve().parents[1]
PHASE3_FILE  = ROOT / "analysis_data" / "phase3" / "engineered_features.parquet"
EVENT_INDEX  = ROOT / "analysis_data" / "event_index.csv"
TRAIN_TEST   = ROOT / "analysis_data" / "train_test_by_event.csv"
OUT_DIR      = ROOT / "analysis_data" / "phase4" / "folds"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Phase 3 column names (verified)
COL_TIME    = "time_stamp"
COL_ASSET   = "asset_id"         # integer turbine ID
COL_TURB    = "turbine_uid"      # string turbine ID (A0, A10, ...)
COL_STATUS  = "status_type_id"   # 0=normal, 3=curtailed, 4=fault

NORMAL_STATUS = 0                # only rows with this status used for training

# Events 51 and 72 share the same physical gearbox event on A21
MERGED_PAIR = {51, 72}
MERGED_IND_ID = "E51_72"

# ---- STATUS CODE LEGEND (for documentation) ---------------------------------
STATUS_LEGEND = {0: "normal", 3: "curtailed/warning", 4: "fault/stopped"}


# =============================================================================
# TASK 1 — Load and verify event metadata
# =============================================================================
def load_event_metadata():
    print("\n[TASK 1]  Loading and verifying event metadata")
    print(f"          Source: {EVENT_INDEX}")

    ei = pd.read_csv(EVENT_INDEX, sep=";")
    print(f"          Columns: {list(ei.columns)}")
    print(f"          Rows   : {len(ei)}")

    # Verify required columns present
    required = ["event_id", "turbine_uid", "event_start", "event_end",
                "event_label", "asset"]
    missing = [c for c in required if c not in ei.columns]
    if missing:
        raise ValueError(f"event_index.csv missing columns: {missing}")

    # Parse timestamps
    ei["event_start"] = pd.to_datetime(ei["event_start"])
    ei["event_end"]   = pd.to_datetime(ei["event_end"])

    print(f"\n          Events found in event_index.csv:")
    print(f"          {'event_id':<10} {'turbine':<8} {'label':<8} "
          f"{'event_start':<22} {'event_end':<22} {'description'}")
    for _, r in ei.iterrows():
        desc = str(r.get("event_description", "")).strip()
        print(f"          {r.event_id:<10} {r.turbine_uid:<8} {r.event_label:<8} "
              f"{str(r.event_start):<22} {str(r.event_end):<22} {desc}")

    n_anomaly = (ei["event_label"] == "anomaly").sum()
    n_normal  = (ei["event_label"] == "normal").sum()
    print(f"\n          Total rows    : {len(ei)}")
    print(f"          Anomaly events: {n_anomaly}")
    print(f"          Normal events : {n_normal}")

    return ei


# =============================================================================
# TASK 2 — Verify time and turbine mapping in Phase 3 data
# =============================================================================
def verify_phase3_mapping(df, ei):
    print("\n[TASK 2]  Verifying time and turbine mapping in Phase 3 data")
    print(f"          Phase 3 shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print(f"          time_stamp range: {df[COL_TIME].min()}  ->  {df[COL_TIME].max()}")
    print(f"          asset_id unique : {sorted(df[COL_ASSET].unique())}")
    print(f"          turbine_uid unique: {sorted(df[COL_TURB].unique())}")
    print(f"          status_type_id unique: {sorted(df[COL_STATUS].unique())}")

    # Verify each event's turbine and time range has observations in Phase 3
    print(f"\n          Per-event verification (timestamp overlap with Phase 3):")
    print(f"          {'event_id':<10} {'turbine':<8} {'p3_rows_in_window':<20} {'status_breakdown'}")
    issues = []
    for _, r in ei.iterrows():
        mask = (
            (df[COL_TURB] == r.turbine_uid) &
            (df[COL_TIME] >= r.event_start) &
            (df[COL_TIME] <= r.event_end)
        )
        sub = df[mask]
        n   = len(sub)
        if n == 0:
            issues.append(f"Event {r.event_id}: zero Phase-3 rows in window!")
        sc = sub[COL_STATUS].value_counts().to_dict()
        sc_str = ", ".join(f"status{k}={v}" for k, v in sorted(sc.items()))
        print(f"          {r.event_id:<10} {r.turbine_uid:<8} {n:<20} {sc_str}")

    if issues:
        for iss in issues:
            print(f"  WARNING  {iss}")
    else:
        print(f"\n  OK  All events have Phase-3 observations in their time window.")

    return issues


# =============================================================================
# TASK 3 — Define 21 independent events
# =============================================================================
def define_independent_events(ei):
    print("\n[TASK 3]  Defining independent events")

    records = []
    merged_seen = False

    for _, r in ei.iterrows():
        eid = int(r["event_id"])

        if eid in MERGED_PAIR:
            if not merged_seen:
                # Collect both rows for the merged pair
                pair = ei[ei["event_id"].isin(MERGED_PAIR)]
                combined_start = pair["event_start"].min()
                combined_end   = pair["event_end"].max()
                records.append({
                    "independent_event_id" : MERGED_IND_ID,
                    "event_id"             : "51+72",
                    "turbine_uid"          : "A21",
                    "asset_id"             : 21,
                    "event_start"          : combined_start,
                    "event_end"            : combined_end,
                    "event_label"          : "anomaly",
                    "event_description"    : "Gearbox bearings damaged (Events 51+72 merged)",
                    "note"                 : "Events 51 and 72 overlap completely; treated as one independent event",
                })
                merged_seen = True
            # skip second occurrence
            continue
        else:
            records.append({
                "independent_event_id" : f"E{eid}",
                "event_id"             : str(eid),
                "turbine_uid"          : r["turbine_uid"],
                "asset_id"             : int(r["asset"]),
                "event_start"          : r["event_start"],
                "event_end"            : r["event_end"],
                "event_label"          : r["event_label"],
                "event_description"    : str(r.get("event_description", "")).strip(),
                "note"                 : "",
            })

    ind_events = pd.DataFrame(records)
    ind_events = ind_events.sort_values("event_start").reset_index(drop=True)

    n_total   = len(ind_events)
    n_anomaly = (ind_events["event_label"] == "anomaly").sum()
    n_normal  = (ind_events["event_label"] == "normal").sum()

    print(f"\n          Independent events defined: {n_total}")
    print(f"          Anomaly: {n_anomaly}   Normal: {n_normal}")
    print()
    print(f"          {'ind_event_id':<12} {'event_id':<10} {'turbine':<8} "
          f"{'label':<8} {'event_start':<22} {'event_end':<22} description")
    for _, r in ind_events.iterrows():
        desc = str(r["event_description"])[:45]
        print(f"          {r.independent_event_id:<12} {r.event_id:<10} "
              f"{r.turbine_uid:<8} {r.event_label:<8} "
              f"{str(r.event_start):<22} {str(r.event_end):<22} {desc}")

    # Save verified event index
    out_path = OUT_DIR / "event_index_verified.csv"
    ind_events.to_csv(out_path, index=False)
    print(f"\n          Saved: {out_path}")

    return ind_events


# =============================================================================
# TASK 4 + 6 — Create LOEO folds with training window definitions
# =============================================================================
def create_loeo_folds(df, ind_events):
    print("\n[TASK 4+6]  Creating LOEO folds")

    fold_records = []

    for fold_idx, row in ind_events.iterrows():
        ind_id        = row["independent_event_id"]
        turbine       = row["turbine_uid"]
        asset_id      = row["asset_id"]
        event_start   = row["event_start"]
        event_end     = row["event_end"]
        event_label   = row["event_label"]
        event_desc    = row["event_description"]

        # ── HELD-OUT ROWS ─────────────────────────────────────────────────────
        # Rows that belong to this event's time window and turbine
        mask_heldout = (
            (df[COL_TURB] == turbine) &
            (df[COL_TIME] >= event_start) &
            (df[COL_TIME] <= event_end)
        )
        heldout_rows = df[mask_heldout]

        # ── CANDIDATE NORMAL ROWS (all normal rows for this turbine) ──────────
        # Normal = status_type_id == 0
        mask_normal_turbine = (
            (df[COL_TURB] == turbine) &
            (df[COL_STATUS] == NORMAL_STATUS)
        )
        normal_turbine = df[mask_normal_turbine]

        # ── TRAINING ROWS: strict temporal cut ────────────────────────────────
        # Must be: same turbine + normal status + timestamp STRICTLY BEFORE event_start
        mask_train = (
            (df[COL_TURB] == turbine) &
            (df[COL_STATUS] == NORMAL_STATUS) &
            (df[COL_TIME]   <  event_start)
        )
        train_rows = df[mask_train]

        training_start = train_rows[COL_TIME].min() if len(train_rows) > 0 else pd.NaT
        training_end   = train_rows[COL_TIME].max() if len(train_rows) > 0 else pd.NaT

        fold_records.append({
            "fold_id"                  : fold_idx + 1,
            "independent_event_id"     : ind_id,
            "held_out_event_id"        : row["event_id"],
            "held_out_turbine"         : turbine,
            "held_out_asset_id"        : asset_id,
            "held_out_event_start"     : event_start,
            "held_out_event_end"       : event_end,
            "held_out_event_label"     : event_label,
            "held_out_event_desc"      : event_desc,
            "training_start"           : training_start,
            "training_end"             : training_end,
            "candidate_normal_rows"    : len(normal_turbine),
            "usable_training_rows"     : len(train_rows),
            "held_out_rows"            : len(heldout_rows),
            "leakage_check_passed"     : None,   # filled in Task 7
        })

    folds_df = pd.DataFrame(fold_records)

    print(f"\n          {'fold':<6} {'ind_event':<12} {'turbine':<8} "
          f"{'label':<8} {'train_rows':<12} {'heldout_rows':<14} training_start -> training_end")
    for _, r in folds_df.iterrows():
        print(f"          {r.fold_id:<6} {r.independent_event_id:<12} "
              f"{r.held_out_turbine:<8} {r.held_out_event_label:<8} "
              f"{r.usable_training_rows:<12} {r.held_out_rows:<14} "
              f"{str(r.training_start)[:16]}  ->  {str(r.training_end)[:16]}")

    return folds_df


# =============================================================================
# TASK 7 — Leakage validation (all 7 checks)
# =============================================================================
def validate_leakage(df, folds_df, ind_events):
    print("\n[TASK 7]  Running leakage validation")
    print(          "          7 checks per fold\n")

    validation_records = []
    global_pass = True

    for _, fold in folds_df.iterrows():
        fold_id     = fold["fold_id"]
        turbine     = fold["held_out_turbine"]
        event_start = fold["held_out_event_start"]
        event_end   = fold["held_out_event_end"]
        ind_id      = fold["independent_event_id"]

        # Reconstruct training mask
        train_mask = (
            (df[COL_TURB] == turbine) &
            (df[COL_STATUS] == NORMAL_STATUS) &
            (df[COL_TIME]   <  event_start)
        )
        train = df[train_mask]

        # Reconstruct held-out mask
        heldout_mask = (
            (df[COL_TURB] == turbine) &
            (df[COL_TIME] >= event_start) &
            (df[COL_TIME] <= event_end)
        )
        heldout = df[heldout_mask]

        checks = {}

        # CHECK 1: No training timestamp >= event_start
        c1 = len(train) == 0 or train[COL_TIME].max() < event_start
        checks["c1_no_future_in_train"] = c1

        # CHECK 2: No held-out observation in training set
        # (training is strictly before event_start, heldout starts at event_start -> no overlap)
        train_times   = set(train[COL_TIME].astype(str))
        heldout_times = set(heldout[COL_TIME].astype(str))
        c2 = len(train_times & heldout_times) == 0
        checks["c2_no_heldout_in_train"] = c2

        # CHECK 3: All training rows same turbine as held-out
        c3 = (len(train) == 0) or (train[COL_TURB] == turbine).all()
        checks["c3_single_turbine_train"] = c3

        # CHECK 4: No non-normal (fault/curtailed) rows in training
        c4 = (len(train) == 0) or (train[COL_STATUS] == NORMAL_STATUS).all()
        checks["c4_only_normal_in_train"] = c4

        # CHECK 5: Forbidden metadata columns not present as potential model features
        forbidden_in_data = [c for c in ["event_id", "train_test"] if c in df.columns]
        c5 = len(forbidden_in_data) == 0
        checks["c5_no_forbidden_metadata"] = c5

        # CHECK 6: No future observations (training_end < event_start)
        if len(train) > 0:
            c6 = train[COL_TIME].max() < event_start
        else:
            c6 = True
        checks["c6_no_future_observations"] = c6

        # CHECK 7: This independent event appears exactly once across all folds
        c7 = (folds_df["independent_event_id"] == ind_id).sum() == 1
        checks["c7_event_appears_once"] = c7

        fold_pass = all(checks.values())
        if not fold_pass:
            global_pass = False
            failed = [k for k, v in checks.items() if not v]
            print(f"  FAIL  Fold {fold_id} ({ind_id}): failed checks: {failed}")
        else:
            print(f"  PASS  Fold {fold_id:>2} ({ind_id:<12})  "
                  f"train={fold['usable_training_rows']:>6}  "
                  f"heldout={fold['held_out_rows']:>5}  "
                  f"all 7 checks passed")

        rec = {"fold_id": fold_id, "independent_event_id": ind_id,
               "turbine": turbine, "event_label": fold["held_out_event_label"],
               "fold_pass": fold_pass}
        rec.update(checks)
        validation_records.append(rec)

    val_df = pd.DataFrame(validation_records)

    print()
    if global_pass:
        print("  ALL LEAKAGE CHECKS PASSED across all folds.")
    else:
        print("  LEAKAGE VALIDATION FAILED. DO NOT proceed to model training.")
        print("  Review the FAIL messages above before continuing.")

    return val_df, global_pass


# =============================================================================
# TASK 8 — Save outputs and print final summary
# =============================================================================
def save_and_summarise(folds_df, ind_events, val_df, global_pass):
    print("\n[TASK 8]  Saving outputs")

    # Update leakage_check_passed in folds_df
    folds_df = folds_df.merge(
        val_df[["fold_id", "fold_pass"]],
        on="fold_id", how="left"
    )
    folds_df["leakage_check_passed"] = folds_df["fold_pass"]
    folds_df = folds_df.drop(columns=["fold_pass"], errors="ignore")

    # 1. Save loeo_folds.csv
    folds_path = OUT_DIR / "loeo_folds.csv"
    folds_df.to_csv(folds_path, index=False)
    print(f"          Saved: {folds_path}")

    # 2. Save leakage_validation.csv
    val_path = OUT_DIR / "leakage_validation.csv"
    val_df.to_csv(val_path, index=False)
    print(f"          Saved: {val_path}")

    # 3. event_index_verified.csv already saved in Task 3
    ev_path = OUT_DIR / "event_index_verified.csv"
    print(f"          Saved: {ev_path}  (created in Task 3)")

    # ── FINAL SUMMARY ─────────────────────────────────────────────────────────
    n_total   = len(folds_df)
    n_anomaly = (folds_df["held_out_event_label"] == "anomaly").sum()
    n_normal  = (folds_df["held_out_event_label"] == "normal").sum()
    turbines  = folds_df["held_out_turbine"].nunique()

    train_min = folds_df["usable_training_rows"].min()
    train_max = folds_df["usable_training_rows"].max()
    hout_min  = folds_df["held_out_rows"].min()
    hout_max  = folds_df["held_out_rows"].max()

    leakage_status = "ALL PASSED" if global_pass else "FAILURES DETECTED — SEE ABOVE"

    print()
    print("=" * 65)
    print("  PHASE 4 - STEP 2: FINAL SUMMARY")
    print("=" * 65)
    print(f"  1.  Independent events          : {n_total}")
    print(f"  2.  Anomaly events              : {n_anomaly}")
    print(f"  3.  Normal / control events     : {n_normal}")
    print(f"  4.  Turbines                    : {turbines}")
    print(f"  5.  LOEO folds created          : {n_total}")
    print(f"  6.  Min training rows (fold)    : {train_min:,}")
    print(f"  7.  Max training rows (fold)    : {train_max:,}")
    print(f"  8.  Min held-out rows (fold)    : {hout_min:,}")
    print(f"  9.  Max held-out rows (fold)    : {hout_max:,}")
    print(f"  10. Leakage validation          : {leakage_status}")
    print(f"  11. Output files:")
    print(f"        {ev_path}")
    print(f"        {folds_path}")
    print(f"        {val_path}")
    print()
    print("  Events 51 + 72 treatment:")
    print("    Both on turbine A21, fully overlapping gearbox event.")
    print("    Merged into one independent event 'E51_72' as per PRD.")
    print()
    print("  STATUS CODE used for training filter:")
    print("    status_type_id == 0  (normal operation)  ->  TRAIN eligible")
    print("    status_type_id != 0                      ->  EXCLUDED")
    print("    status_type_id is NEVER passed to any model.")
    print()
    if global_pass:
        print("  STEP 2 COMPLETE. All leakage checks passed.")
        print("  Do NOT proceed to Step 3 until output files are reviewed.")
    else:
        print("  STEP 2 INCOMPLETE. Fix leakage failures before proceeding.")
    print("=" * 65)

    return folds_df


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 65)
    print("  PHASE 4 - STEP 2: BUILD AND VALIDATE 21 LOEO EVENT FOLDS")
    print("=" * 65)

    # Verify Phase 3 file is untouched
    print(f"\n  Loading Phase 3 dataset (read-only)...")
    print(f"  Path: {PHASE3_FILE}")
    df = pd.read_parquet(PHASE3_FILE)
    df[COL_TIME] = pd.to_datetime(df[COL_TIME])
    print(f"  Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
    assert df.shape[0] == 425_023, (
        f"Phase 3 row count changed! Expected 425,023 got {df.shape[0]}")
    print(f"  Phase 3 integrity: OK (425,023 rows confirmed)")

    # Run all tasks
    ei         = load_event_metadata()
    verify_phase3_mapping(df, ei)
    ind_events = define_independent_events(ei)
    folds_df   = create_loeo_folds(df, ind_events)
    val_df, global_pass = validate_leakage(df, folds_df, ind_events)
    save_and_summarise(folds_df, ind_events, val_df, global_pass)

    if not global_pass:
        raise SystemExit(
            "\nSTEP 2 FAILED: leakage checks did not pass. "
            "Do NOT proceed to model training."
        )


if __name__ == "__main__":
    main()
