"""
Phase 4 - Step 8: Component Attribution & Root-Cause Heatmap Matrix
====================================================================
Pass MODEL_NAME as sys.argv[1]: "ridge", "dt", "rf", "xgb"
Default: "ridge"
"""
import json, sys, warnings
import numpy as np, pandas as pd
from pathlib import Path

MODEL_NAME = sys.argv[1].lower() if len(sys.argv) > 1 else "ridge"

ROOT = Path(__file__).resolve().parents[1]
COMP_FILE = ROOT / "analysis_data" / "phase4" / "evaluation" / MODEL_NAME / "component_scores.parquet"
EVENT_FILE = ROOT / "analysis_data" / "phase4" / "evaluation" / MODEL_NAME / "event_scores.parquet"
OUT_DIR = ROOT / "analysis_data" / "phase4" / "attribution" / MODEL_NAME
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print(f"\n=======================================================")
    print(f" Phase 4 Step 8 — Component Attribution ({MODEL_NAME.upper()})")
    print(f"=======================================================")

    if not COMP_FILE.exists():
        print(f"Error: {COMP_FILE} does not exist.")
        return

    comp_df = pd.read_parquet(COMP_FILE)
    event_df = pd.read_parquet(EVENT_FILE)

    # Pivot to create event x component matrix of scores
    pivot_score = comp_df.pivot(index="independent_event_id", columns="component_group", values="component_score")
    pivot_p95   = comp_df.pivot(index="independent_event_id", columns="component_group", values="component_p95")

    # Join metadata
    meta = event_df[["independent_event_id", "turbine_uid", "event_label", "event_median_score", "event_p95_score"]].drop_duplicates("independent_event_id").set_index("independent_event_id")

    matrix_score = meta.join(pivot_score).reset_index()
    matrix_p95   = meta.join(pivot_p95).reset_index()

    # Identify primary anomaly driver per event (component with max score)
    comp_cols = [c for c in pivot_score.columns]
    
    primary_drivers = []
    for idx, row in matrix_score.iterrows():
        scores = {c: row[c] for c in comp_cols if pd.notna(row[c])}
        if scores:
            top_comp = max(scores, key=scores.get)
            top_val  = scores[top_comp]
        else:
            top_comp = "Unknown"
            top_val  = 0.0
        primary_drivers.append({"independent_event_id": row["independent_event_id"], "primary_component": top_comp, "primary_component_score": top_val})

    driver_df = pd.DataFrame(primary_drivers)
    final_summary = matrix_score.merge(driver_df, on="independent_event_id")

    final_summary.to_csv(OUT_DIR / "component_attribution_matrix.csv", index=False)
    final_summary.to_parquet(OUT_DIR / "component_attribution_matrix.parquet", index=False)

    print(f"SUCCESS: Created component attribution matrix for {MODEL_NAME.upper()}")
    print(f"Saved to {OUT_DIR / 'component_attribution_matrix.csv'}")

if __name__ == "__main__":
    main()
