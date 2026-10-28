"""
Phase 4 - Step 7: Unified Multi-Model Evaluation & Strategy Comparison
========================================================================
Compares 4 NBM Model Architectures:
  1. Ridge Regression NBM
  2. Decision Tree Regressor NBM
  3. Random Forest Regressor NBM
  4. XGBoost Regressor NBM

Across 3 Aggregation Strategies:
  A. Event Median Score
  B. Event 95th Percentile (P95) Score
  C. Persistence Score (fraction of observations with composite z > 2.5)

Outputs:
  - evaluation_summary.parquet & .csv
  - model_comparison_report.json
  - best_model_config.json
"""
import json, sys, warnings
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc, f1_score, precision_score, recall_score, roc_curve

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "analysis_data" / "phase4" / "evaluation"
OUT_DIR = EVAL_DIR / "unified"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = ["ridge", "dt", "rf", "xgb"]
STRATEGIES = ["event_median_score", "event_p95_score", "persistence_score"]

def evaluate_model_strategy(df, model_name, strategy_col):
    """Compute comprehensive diagnostic metrics for a specific model + strategy."""
    clean_df = df.dropna(subset=[strategy_col, "event_label"]).copy()
    y_true = (clean_df["event_label"] == "anomaly").astype(int).values
    y_scores = clean_df[strategy_col].values.astype(np.float64)

    if len(np.unique(y_true)) < 2:
        return None

    # ROC-AUC
    roc_auc = float(roc_auc_score(y_true, y_scores))
    
    # PR-AUC
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_scores)
    pr_auc = float(auc(recalls, precisions))

    # Find optimal threshold using max F1
    f1_scores = np.where((precisions + recalls) > 0, 2 * (precisions * recalls) / (precisions + recalls), 0)
    best_idx = np.argmax(f1_scores)
    best_thresh = float(thresholds[best_idx]) if best_idx < len(thresholds) else float(np.median(y_scores))
    
    y_pred = (y_scores >= best_thresh).astype(int)
    
    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    return {
        "model": model_name,
        "strategy": strategy_col,
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "optimal_threshold": round(best_thresh, 4),
        "f1_max": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "fpr": round(fpr, 4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "total_events": len(y_true),
        "anomaly_events": int(np.sum(y_true)),
        "normal_events": int(len(y_true) - np.sum(y_true))
    }

def main():
    print("=========================================================================")
    print(" Phase 4 Step 7 — Unified Multi-Model Evaluation & Threshold Selection")
    print("=========================================================================")

    results = []
    
    for model in MODELS:
        event_scores_file = EVAL_DIR / model / "event_scores.parquet"
        if not event_scores_file.exists():
            print(f"Skipping {model.upper()} (event_scores.parquet not found yet)")
            continue
            
        df = pd.read_parquet(event_scores_file)
        print(f"\nEvaluating {model.upper()} across {len(df)} events ...")

        for strat in STRATEGIES:
            res = evaluate_model_strategy(df, model, strat)
            if res:
                results.append(res)
                print(f"  [{strat.ljust(20)}] ROC-AUC={res['roc_auc']:.4f} | PR-AUC={res['pr_auc']:.4f} | F1={res['f1_max']:.4f} (Thresh={res['optimal_threshold']})")

    if not results:
        print("\nNo model evaluation results available yet.")
        return

    res_df = pd.DataFrame(results).sort_values("roc_auc", ascending=False).reset_index(drop=True)
    
    # Save results
    res_df.to_csv(OUT_DIR / "model_comparison_summary.csv", index=False)
    res_df.to_parquet(OUT_DIR / "model_comparison_summary.parquet", index=False)
    
    best_row = res_df.iloc[0].to_dict()
    with open(OUT_DIR / "best_model_config.json", "w") as f:
        json.dump(best_row, f, indent=2)

    print("\n-------------------------------------------------------------------------")
    print(f" TOP PERFORMING CONFIGURATION: {best_row['model'].upper()} with {best_row['strategy']}")
    print(f"   ROC-AUC: {best_row['roc_auc']} | PR-AUC: {best_row['pr_auc']} | Max F1: {best_row['f1_max']}")
    print(f"   Optimal Threshold: {best_row['optimal_threshold']}")
    print("-------------------------------------------------------------------------")
    print(f"Saved summary to {OUT_DIR / 'model_comparison_summary.csv'}")

if __name__ == "__main__":
    main()
