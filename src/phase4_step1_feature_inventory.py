"""
Phase 4 - Step 1: Feature Inventory & Role Assignment
======================================================
What this script does (plain English):
  1. Loads the frozen Phase 3 dataset (engineered_features.parquet).
  2. Confirms it has exactly 425,023 rows and the expected columns.
  3. Labels every column with ONE of four roles:
       - CONDITIONING  : operating-condition inputs to the NBM
       - TARGET        : health-related sensors the NBM will predict
       - FORBIDDEN     : must NEVER enter any model
       - META          : timestamps / turbine IDs for indexing only
  4. Saves two CSVs to analysis_data/phase4/feature_selection/:
       - selected_features.csv  : full column catalogue with roles
       - feature_groups.csv     : target columns grouped by component
  5. Prints a human-readable summary.

Run with:
    python src/phase4_step1_feature_inventory.py
"""

import pandas as pd
from pathlib import Path

# ---- PATHS ------------------------------------------------------------------
ROOT        = Path(__file__).resolve().parents[1]
PHASE3_FILE = ROOT / "analysis_data" / "phase3" / "engineered_features.parquet"
OUT_DIR     = ROOT / "analysis_data" / "phase4" / "feature_selection"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_ROWS = 425_023

# ---- ROLE DEFINITIONS (PRD sections 7, 8, 9) --------------------------------

FORBIDDEN = {
    "status_type_id" : "event label - used only offline to filter training rows",
    "train_test"     : "split label - encodes which events are anomalies",
    "event_id"       : "event identifier - leaks event membership",
    "asset_id"       : "turbine identifier - meta only",
    "turbine_uid"    : "turbine identifier - meta only",
    "sensor_46"      : "defective / constant sensor identified in Phase 2",
    "sensor_49"      : "defective / constant sensor identified in Phase 2",
}

META = {
    "timestamp"  : "primary time index",
    "turbine_id" : "turbine identifier for per-turbine model selection",
}

CONDITIONING = {
    "power_30_avg"     : "power output (load) - 30-second average",
    "wind_speed_3_avg" : "wind speed - 3-second average",
    "sensor_18_avg"    : "generator RPM - rotational condition",
    "sensor_52_avg"    : "rotor RPM - mechanical condition",
    "sensor_0_avg"     : "ambient temperature - environmental condition",
    "op_power_bin"     : "operating power bin - load regime category",
    "op_wind_bin"      : "operating wind bin - wind regime category",
    "sensor_5_avg"     : "pitch angle - blade/load control condition",
}

# Format: column_name -> (component_group, description)
TARGETS = {
    # GEARBOX
    "dT_gbx_brg"                : ("Gearbox",              "gearbox bearing temperature rise above ambient"),
    "dT_gbx_oil"                : ("Gearbox",              "gearbox oil temperature rise above ambient"),
    "gbx_brg_minus_oil"         : ("Gearbox",              "bearing vs oil temp differential"),
    # GENERATOR BEARING
    "dT_genbrg_de"              : ("Generator_Bearing",    "generator drive-end bearing temp rise"),
    "dT_genbrg_nde"             : ("Generator_Bearing",    "generator non-drive-end bearing temp rise"),
    "genbrg_de_minus_nde"       : ("Generator_Bearing",    "DE vs NDE bearing differential"),
    # HYDRAULIC
    "dT_hyd_oil"                : ("Hydraulic",            "hydraulic oil temperature rise"),
    "sensor_5_std"              : ("Hydraulic",            "pitch angle std dev - hydraulic activity proxy"),
    "sensor_5_std__mean_24h"    : ("Hydraulic",            "24h rolling mean of pitch std dev"),
    # TRANSFORMER
    "dT_trafo"                  : ("Transformer",          "transformer temperature rise above ambient"),
    "trafo_spread"              : ("Transformer",          "transformer winding temperature spread"),
    "dT_trafo__mean_24h"        : ("Transformer",          "24h rolling mean of transformer temp rise"),
    # GENERATOR ELECTRICAL
    "dT_stator"                 : ("Generator_Electrical", "stator winding temperature rise"),
    "stator_spread"             : ("Generator_Electrical", "stator winding temperature spread"),
    "dT_splitring"              : ("Generator_Electrical", "slip-ring temperature rise"),
    # MECHANICAL
    "gear_ratio"                : ("Mechanical",           "generator RPM / rotor RPM ratio"),
    "gear_ratio__std_24h"       : ("Mechanical",           "24h rolling std dev of gear ratio"),
    "tsr_proxy"                 : ("Mechanical",           "tip-speed ratio proxy"),
    # POWER
    "power_curve_dev"           : ("Power",                "deviation from expected power curve"),
    "power_curve_dev__mean_24h" : ("Power",                "24h rolling mean of power curve deviation"),
    "power_curve_dev__slope_24h": ("Power",                "24h rolling slope of power curve deviation"),
}


# =============================================================================
def main():
    print("=" * 65)
    print("  PHASE 4 - STEP 1: FEATURE INVENTORY")
    print("=" * 65)

    # 1. LOAD
    print(f"\n[1/5]  Loading Phase 3 dataset ...")
    print(f"       {PHASE3_FILE}")
    df = pd.read_parquet(PHASE3_FILE)
    actual_rows, actual_cols = df.shape
    print(f"       Shape: {actual_rows:,} rows  x  {actual_cols} columns")

    # 2. VALIDATE ROW COUNT
    print(f"\n[2/5]  Validating row count ...")
    if actual_rows == EXPECTED_ROWS:
        print(f"       OK  Row count matches expected ({EXPECTED_ROWS:,})")
    else:
        print(f"       WARNING  Expected {EXPECTED_ROWS:,} rows, got {actual_rows:,}")

    # 3. CHECK DEFINED COLUMNS EXIST
    print(f"\n[3/5]  Checking defined columns exist in the dataset ...")
    all_cols = set(df.columns)

    def check_group(label, keys):
        missing = [c for c in keys if c not in all_cols]
        if missing:
            print(f"       MISSING {label}: {missing}")
        else:
            print(f"       OK  All {label} columns found")
        return missing

    check_group("CONDITIONING", CONDITIONING)
    missing_targets = check_group("TARGET", TARGETS)
    check_group("FORBIDDEN",    FORBIDDEN)
    check_group("META",         META)

    # 4. BUILD FULL CATALOGUE
    print(f"\n[4/5]  Building feature catalogue ...")
    all_defined = set(FORBIDDEN) | set(META) | set(CONDITIONING) | set(TARGETS)
    unlabelled  = [c for c in df.columns if c not in all_defined]

    rows = []
    for col in df.columns:
        if col in FORBIDDEN:
            role, group, desc = "FORBIDDEN", "", FORBIDDEN[col]
        elif col in META:
            role, group, desc = "META", "", META[col]
        elif col in CONDITIONING:
            role, group, desc = "CONDITIONING", "Operating_Conditions", CONDITIONING[col]
        elif col in TARGETS:
            grp, d = TARGETS[col]
            role, group, desc = "TARGET", grp, d
        else:
            role, group, desc = "UNLABELLED", "", ""
        rows.append({"column": col, "role": role,
                     "component_group": group, "description": desc})

    catalogue = pd.DataFrame(rows)
    feat_path = OUT_DIR / "selected_features.csv"
    catalogue.to_csv(feat_path, index=False)
    print(f"       Saved: {feat_path}")

    # BUILD COMPONENT GROUP TABLE
    target_rows = []
    for col, (grp, desc) in TARGETS.items():
        target_rows.append({
            "component_group" : grp,
            "column"          : col,
            "description"     : desc,
            "in_phase3_data"  : col in all_cols,
        })
    groups_df   = pd.DataFrame(target_rows).sort_values(["component_group", "column"])
    groups_path = OUT_DIR / "feature_groups.csv"
    groups_df.to_csv(groups_path, index=False)
    print(f"       Saved: {groups_path}")

    # 5. SUMMARY
    print(f"\n[5/5]  ROLE SUMMARY")
    print(f"       {'-' * 45}")
    role_counts = catalogue["role"].value_counts()
    for role in ["CONDITIONING", "TARGET", "META", "FORBIDDEN", "UNLABELLED"]:
        count = role_counts.get(role, 0)
        print(f"       {role:<16}  {count:>4}  columns")

    print(f"\n       Target features by component:")
    comp_counts = (
        catalogue[catalogue["role"] == "TARGET"]
        .groupby("component_group").size()
        .sort_values(ascending=False)
    )
    for comp, n in comp_counts.items():
        print(f"         {comp:<28}  {n} target(s)")

    if missing_targets:
        print(f"\n  WARNING  {len(missing_targets)} TARGET column(s) not in Phase 3 data:")
        for c in missing_targets:
            print(f"     - {c}  ({TARGETS[c][0]})")
        print(f"     These will be skipped during modelling.")
        print(f"     Tip: check feature_manifest.csv for correct column names.")
    else:
        print(f"\n  OK  All {len(TARGETS)} target features confirmed in Phase 3 data.")

    if unlabelled:
        print(f"\n  NOTE  {len(unlabelled)} columns are UNLABELLED (will be ignored by NBM).")
        print(f"        First 10: {unlabelled[:10]}")

    print(f"\n{'=' * 65}")
    print(f"  Step 1 complete.")
    print(f"  Outputs: analysis_data/phase4/feature_selection/")
    print(f"  Next   : Step 2 - Build 21 LOEO event folds")
    print(f"{'=' * 65}\n")


if __name__ == "__main__":
    main()
