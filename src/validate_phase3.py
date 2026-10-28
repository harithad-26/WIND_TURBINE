"""
PHASE 3 validation. Read-only except analysis_data/phase3/validation_summary.json.

The two checks that actually PROVE the rules held, rather than asserting them:

  ISOLATION PROBE  recompute one turbine entirely on its own and require the
                   result to be bitwise identical to its slice of the full run.
                   Any cross-turbine contamination breaks this.

  FUTURE PROBE     corrupt every observation AFTER a cut time, recompute, and
                   require every feature at or before the cut to be unchanged.
                   Any forward-looking window breaks this.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase3_features as P3  # noqa: E402

IN = P3.IN
OUTDIR = P3.OUTDIR
FEAT = os.path.join(OUTDIR, "engineered_features.parquet")


def sect(t):
    print("\n" + "=" * 76)
    print(t)
    print("=" * 76)


def main():
    R = {}
    src = pd.read_parquet(IN).sort_values(["turbine_uid", "time_stamp"]).reset_index(drop=True)
    out = pd.read_parquet(FEAT)
    meta = json.load(open(os.path.join(OUTDIR, "_build_meta.json")))
    eng = meta["eng_cols"]
    mani = pd.read_csv(os.path.join(OUTDIR, "feature_manifest.csv"))

    sect("1. STRUCTURE")
    R["in_rows"], R["in_cols"] = int(len(src)), int(src.shape[1])
    R["out_rows"], R["out_cols"] = int(len(out)), int(out.shape[1])
    R["n_engineered"] = len(eng)
    R["rows_preserved"] = bool(len(out) == 425023 == len(src))
    R["n_turbines"] = int(out.turbine_uid.nunique())
    R["assets"] = sorted(int(a) for a in out.asset_id.unique())
    print("  input          : {:,} x {}".format(R["in_rows"], R["in_cols"]))
    print("  output         : {:,} x {}".format(R["out_rows"], R["out_cols"]))
    print("  engineered     : {}".format(R["n_engineered"]))
    print("  rows == 425,023: {}".format(R["rows_preserved"]))
    print("  turbines       : {} {}".format(R["n_turbines"], sorted(out.turbine_uid.unique())))
    print("  asset ids      : {}".format(R["assets"]))
    R["all_source_cols_retained"] = bool(set(src.columns) <= set(out.columns))
    print("  all 85 input columns retained: {}".format(R["all_source_cols_retained"]))

    sect("2. TIMESTAMP INTEGRITY / ORDERING / DUPLICATES")
    m = out[["turbine_uid", "asset_id", "time_stamp"]].merge(
        src[["turbine_uid", "asset_id", "time_stamp"]],
        on=["turbine_uid", "asset_id", "time_stamp"], how="inner")
    R["timestamps_identical_to_input"] = bool(len(m) == len(src))
    mono = out.groupby("turbine_uid").time_stamp.apply(lambda s: s.is_monotonic_increasing)
    R["chronological_per_turbine"] = bool(mono.all())
    R["duplicate_rows"] = int(out.duplicated(subset=["turbine_uid", "time_stamp"]).sum())
    print("  timestamps match input exactly : {}".format(R["timestamps_identical_to_input"]))
    print("  chronological within turbine   : {}".format(dict(mono)))
    print("  duplicate (turbine,timestamp)  : {}".format(R["duplicate_rows"]))

    sect("3. LEAKAGE - forbidden columns must not appear among engineered features")
    bad = [c for c in eng if c in P3.FORBIDDEN]
    R["forbidden_in_engineered"] = bad
    print("  forbidden columns used as features : {}".format(bad or "NONE"))
    # Exclude BOTH marker types: "EXCLUDED" and "EXCLUDED_DEFECTIVE" rows exist
    # only to record what was deliberately kept out, and name themselves as source.
    real = mani[~mani.feature_type.astype(str).str.startswith("EXCLUDED")]
    derived_from = " ".join(real["source_column(s)"].astype(str))
    leaky_src = [c for c in ("status_type_id", "event_id", "row_id_in_event",
                             "train_test", "time_offset_days") if c in derived_from]
    R["forbidden_as_source"] = leaky_src
    print("  forbidden columns as a SOURCE      : {}".format(leaky_src or "NONE"))
    defect_used = [c for c in P3.DEFECTIVE if c in derived_from]
    R["defective_used_in_derivation"] = defect_used
    print("  defective columns in derivations   : {}".format(defect_used or "NONE"))
    print("  status_type_id present as passthrough only: {}".format(
        "status_type_id" in out.columns and "status_type_id" not in eng))
    R["no_target_column"] = not any(
        k in out.columns for k in ("label", "target", "y", "event_label", "is_anomaly"))
    print("  no target/label column created     : {}".format(R["no_target_column"]))

    sect("4. NUMERIC HEALTH")
    E = out[eng]
    arr = E.to_numpy(dtype="float64")
    R["infinite_values"] = int(np.isinf(arr).sum())
    nan_total = int(np.isnan(arr).sum())
    R["nan_total_engineered"] = nan_total
    R["nan_pct_engineered"] = round(nan_total / arr.size * 100, 4)
    print("  infinite values in engineered   : {}".format(R["infinite_values"]))
    print("  NaN cells in engineered         : {:,} of {:,} ({:.3f}%)".format(
        nan_total, arr.size, R["nan_pct_engineered"]))
    src_nan = src.isna().sum()
    src_nan = src_nan[src_nan > 0]
    R["source_nan"] = {k: int(v) for k, v in src_nan.items()}
    print("  source NaN preserved (not filled): {}".format(R["source_nan"]))
    for c in ("sensor_14_avg", "sensor_22_avg"):
        assert int(out[c].isna().sum()) == int(src[c].isna().sum())
    print("  -> raw NaN counts identical in output: True (no interpolation applied)")

    top = E.isna().sum().sort_values(ascending=False)
    print("\n  highest-NaN engineered features (warm-up / gap driven):")
    for k, v in top.head(6).items():
        print("    {:<34} {:>7,}  ({:.2f}%)".format(k, int(v), v / len(out) * 100))
    print("  features with zero NaN: {} of {}".format(int((top == 0).sum()), len(eng)))
    R["nan_by_feature"] = {k: int(v) for k, v in top.items() if v > 0}
    R["features_over_20pct_nan"] = {k: round(float(v) / len(out) * 100, 2)
                                    for k, v in top.items() if v / len(out) > 0.20}
    print("  features above 20% NaN: {}".format(R["features_over_20pct_nan"] or "none"))
    R["warmup_rows_no_full_7d"] = int((out["win_has_full_7d"] == 0).sum())
    print("  rows without a full 7d window: {:,} ({:.2f}%)".format(
        R["warmup_rows_no_full_7d"], R["warmup_rows_no_full_7d"] / len(out) * 100))

    sect("5. ISOLATION PROBE - recompute one turbine alone, require bitwise equality")
    uid = "A11"
    g = src[src.turbine_uid == uid].set_index("time_stamp")
    solo = P3.build_turbine(g).astype("float32").reset_index()
    ref = out[out.turbine_uid == uid].reset_index(drop=True)
    cols = [c for c in solo.columns if c != "time_stamp"]
    a = solo[cols].to_numpy(dtype="float64")
    b = ref[cols].to_numpy(dtype="float64")
    same = ((a == b) | (np.isnan(a) & np.isnan(b))).all()
    R["isolation_bitwise_identical"] = bool(same)
    print("  turbine {} recomputed alone: {:,} rows x {} features".format(uid, len(solo), len(cols)))
    print("  bitwise identical to full-run slice: {}".format(same))
    print("  -> no cross-turbine information entered {}'s features".format(uid))

    sect("6. FUTURE PROBE - corrupt everything after a cut time, recompute")
    g = src[src.turbine_uid == uid].set_index("time_stamp")
    cut = g.index[len(g) // 2]
    corrupt = g.copy()
    num = [c for c in corrupt.columns if pd.api.types.is_numeric_dtype(corrupt[c])
           and c != "asset_id"]
    fut = corrupt.index > cut
    corrupt.loc[fut, num] = corrupt.loc[fut, num] * -7.0 + 1234.0
    cf = P3.build_turbine(corrupt).astype("float32")
    base = P3.build_turbine(g).astype("float32")
    past = base.index <= cut
    a = base.loc[past, cols].to_numpy(dtype="float64")
    b = cf.loc[past, cols].to_numpy(dtype="float64")
    same_past = ((a == b) | (np.isnan(a) & np.isnan(b))).all()
    changed_future = not ((base.loc[~past, cols].to_numpy(dtype="float64") ==
                           cf.loc[~past, cols].to_numpy(dtype="float64")) |
                          (np.isnan(base.loc[~past, cols].to_numpy(dtype="float64")) &
                           np.isnan(cf.loc[~past, cols].to_numpy(dtype="float64")))).all()
    R["future_probe_past_unchanged"] = bool(same_past)
    R["future_probe_future_changed"] = bool(changed_future)
    print("  cut time                        : {}".format(cut))
    print("  rows at/before cut              : {:,}".format(int(past.sum())))
    print("  features at/before cut UNCHANGED: {}".format(same_past))
    print("  features after cut DID change   : {}  (probe is effective)".format(changed_future))
    print("  -> no feature reads a future observation")

    sect("7. MANUAL SPOT CHECKS against the underlying observations")
    rng = np.random.default_rng(20260909)
    checks, ok_all = [], True
    for _ in range(6):
        t_uid = rng.choice(sorted(src.turbine_uid.unique()))
        gg = src[src.turbine_uid == t_uid].set_index("time_stamp").sort_index()
        gg = gg[gg.index > gg.index[0] + pd.Timedelta(days=10)]
        ts = gg.index[rng.integers(0, len(gg))]
        ch = gg["sensor_11_avg"] - gg["sensor_0_avg"]           # dT_gbx_brg
        win = ch[(ch.index > ts - pd.Timedelta(hours=24)) & (ch.index <= ts)]
        exp_mean = win.mean() if win.notna().sum() >= P3.MIN_PERIODS["24h"] else np.nan
        exp_rng = (win.max() - win.min()) if win.notna().sum() >= P3.MIN_PERIODS["24h"] else np.nan
        row = out[(out.turbine_uid == t_uid) & (out.time_stamp == ts)].iloc[0]
        got_mean, got_rng = row["dT_gbx_brg__mean_24h"], row["dT_gbx_brg__range_24h"]
        d1 = abs(exp_mean - got_mean) if pd.notna(exp_mean) else 0.0
        d2 = abs(exp_rng - got_rng) if pd.notna(exp_rng) else 0.0
        ok = (d1 < 1e-3) and (d2 < 1e-3)
        ok_all &= ok
        checks.append({"turbine": str(t_uid), "time": str(ts), "n_in_window": int(len(win)),
                       "manual_mean_24h": round(float(exp_mean), 6),
                       "stored_mean_24h": round(float(got_mean), 6),
                       "manual_range_24h": round(float(exp_rng), 6),
                       "stored_range_24h": round(float(got_rng), 6), "match": bool(ok)})
        print("  {} {}  n={:>3}  mean manual={:.4f} stored={:.4f} | range manual={:.4f} "
              "stored={:.4f}  {}".format(t_uid, ts, len(win), exp_mean, got_mean,
                                         exp_rng, got_rng, "OK" if ok else "MISMATCH"))
    # independent slope check
    t_uid = "A0"
    gg = src[src.turbine_uid == t_uid].set_index("time_stamp").sort_index()
    ts = gg.index[50000]
    ch = (gg["sensor_11_avg"] - gg["sensor_0_avg"])
    w = ch[(ch.index > ts - pd.Timedelta(hours=24)) & (ch.index <= ts)].dropna()
    th = (w.index - w.index[0]).total_seconds() / 3600.0
    manual_slope = np.polyfit(th, w.values, 1)[0]
    stored = out[(out.turbine_uid == t_uid) & (out.time_stamp == ts)].iloc[0]["dT_gbx_brg__slope_24h"]
    slope_ok = abs(manual_slope - stored) < 1e-3
    ok_all &= slope_ok
    print("  slope check {} {}: manual={:.6f} stored={:.6f}  {}".format(
        t_uid, ts, manual_slope, stored, "OK" if slope_ok else "MISMATCH"))
    R["spot_checks"] = checks
    R["spot_checks_all_pass"] = bool(ok_all)
    R["slope_check_pass"] = bool(slope_ok)

    sect("8. RESULT")
    crit = {
        "rows_preserved": R["rows_preserved"],
        "turbines_5": R["n_turbines"] == 5,
        "timestamps_identical": R["timestamps_identical_to_input"],
        "chronological": R["chronological_per_turbine"],
        "no_duplicates": R["duplicate_rows"] == 0,
        "no_forbidden_features": not R["forbidden_in_engineered"],
        "no_forbidden_sources": not R["forbidden_as_source"],
        "no_defective_in_derivations": not R["defective_used_in_derivation"],
        "no_target_created": R["no_target_column"],
        "no_infinities": R["infinite_values"] == 0,
        "source_nan_preserved": True,
        "isolation_ok": R["isolation_bitwise_identical"],
        "future_probe_ok": R["future_probe_past_unchanged"] and R["future_probe_future_changed"],
        "spot_checks_ok": R["spot_checks_all_pass"] and R["slope_check_pass"],
        "all_source_cols_retained": R["all_source_cols_retained"],
    }
    for k, v in crit.items():
        print("  {:<32} {}".format(k, "PASS" if v else "FAIL"))
    R["criteria"] = crit
    R["ALL_PASSED"] = all(crit.values())
    print("\n  ALL CHECKS PASSED: {}".format(R["ALL_PASSED"]))

    with open(os.path.join(OUTDIR, "validation_summary.json"), "w") as fh:
        json.dump(R, fh, indent=2, default=str)
    print("  wrote {}/validation_summary.json".format(OUTDIR))
    return 0 if R["ALL_PASSED"] else 1


if __name__ == "__main__":
    sys.exit(main())
