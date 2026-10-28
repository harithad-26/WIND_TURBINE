"""
Phase 4 - Step 9: Feature Contribution & Anomaly Residual Ranking
==================================================================
Pass MODEL_NAME as sys.argv[1]: "ridge", "dt", "rf", "xgb"
Default: "ridge"
"""
import json, sys, warnings
import numpy as np, pandas as pd
from pathlib import Path

MODEL_NAME = sys.argv[1].lower() if len(sys.argv) > 1 else "ridge"

ROOT = Path(__file__).resolve().parents[1]
RES_FILE = ROOT / "analysis_data" / "phase4" / "residuals" / MODEL_NAME / "raw_residuals.parquet"
OUT_DIR  = ROOT / "analysis_data" / "phase4" / "attribution" / MODEL_NAME
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print(f"\n=======================================================")
    print(f" Phase 4 Step 9 — Feature Contribution ({MODEL_NAME.upper()})")
    print(f"=======================================================")

    if not RES_FILE.exists():
        print(f"Error: {RES_FILE} does not exist.")
        return

    res_df = pd.read_parquet(RES_FILE)
    
    tgt_col = None
    for c in ["target_name", "target_column", "target_variable"]:
        if c in res_df.columns:
            tgt_col = c
            break

    res_col = "raw_residual" if "raw_residual" in res_df.columns else "residual"

    target_contrib = res_df.groupby(tgt_col)[res_col].apply(lambda x: float(np.mean(np.abs(x.values)))).reset_index()
    target_contrib.columns = ["target_column", "mean_abs_residual"]

    total_res = target_contrib["mean_abs_residual"].sum()
    target_contrib["pct_contribution"] = (target_contrib["mean_abs_residual"] / total_res * 100.0).round(2)
    target_contrib = target_contrib.sort_values("pct_contribution", ascending=False).reset_index(drop=True)

    target_contrib.to_csv(OUT_DIR / "feature_contribution_ranking.csv", index=False)
    print(f"SUCCESS: Saved feature contribution ranking for {MODEL_NAME.upper()}")
    print(f"Top 5 anomalous channels:\n{target_contrib.head(5).to_string(index=False)}")

if __name__ == "__main__":
    main()
