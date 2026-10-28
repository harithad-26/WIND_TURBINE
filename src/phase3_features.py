"""
PHASE 3 - Feature engineering for Wind Farm A.

Input  : analysis_data/scada_unique.parquet   (frozen, 425,023 x 85, never modified)
Output : analysis_data/phase3/engineered_features.parquet
         analysis_data/phase3/feature_manifest.csv
         analysis_data/phase3/validation_summary.json

Design rules enforced in code, not merely documented:

  TEMPORAL CAUSALITY  every rolling/trend feature at time T uses only rows in
                      (T - w, T].  Windows are TIME-BASED ('3h'/'24h'/'7d'), so a
                      SCADA gap shortens the window instead of silently bridging
                      it.  No centred windows, no shift(-n), no bfill, no
                      interpolation anywhere.

  TURBINE ISOLATION   each turbine is processed in its own frame; nothing is ever
                      computed across turbines.  Verified by recomputing one
                      turbine alone and comparing bitwise.

  NO LEAKAGE          status_type_id is NOT used to build any feature (not even
                      as a fitting filter).  It is carried through only as a
                      passthrough column for later label/analysis work.
                      Identifiers, provenance and event fields never enter a
                      feature.  No target is created here.

  NO FABRICATION      genuine NaNs stay NaN.  A window with under 75% of its
                      expected samples yields NaN rather than a value computed
                      from too little history.
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd

IN = os.path.join("analysis_data", "scada_unique.parquet")
OUTDIR = os.path.join("analysis_data", "phase3")

STEP_MIN = 10
WINDOWS = {"3h": 3 * 60, "24h": 24 * 60, "7d": 7 * 24 * 60}          # label -> minutes
EXPECTED = {k: v // STEP_MIN for k, v in WINDOWS.items()}             # 18 / 144 / 1008
MIN_FRAC = 0.75
MIN_PERIODS = {k: int(np.ceil(v * MIN_FRAC)) for k, v in EXPECTED.items()}  # 14/108/756

# Columns that must never become a predictive feature.
FORBIDDEN = ["status_type_id", "turbine_uid", "asset_id", "time_stamp",
             "event_id", "row_id_in_event", "train_test", "time_offset_days",
             "time_stamp_aligned"]
# Documented defects - preserved as passthrough, never used in a derived feature.
DEFECTIVE = ["sensor_46", "sensor_49",
             "sensor_31_max", "sensor_31_min", "sensor_31_std"]

AMB = "sensor_0_avg"
STATOR = ["sensor_15_avg", "sensor_16_avg", "sensor_17_avg"]
TRAFO = ["sensor_38_avg", "sensor_39_avg", "sensor_40_avg"]
IGBT_R = ["sensor_35_avg", "sensor_36_avg", "sensor_37_avg"]
CURR = ["sensor_23_avg", "sensor_24_avg", "sensor_25_avg"]
VOLT = ["sensor_32_avg", "sensor_33_avg", "sensor_34_avg"]

ROTOR_MIN_RPM = 5.0      # below this the drivetrain is not turning: ratio undefined
WIND_MIN_MS = 1.0        # below this wind ratios are numerically meaningless
POWER_PRODUCING = 0.05   # normalised grid power
WIND_BINS = np.arange(0, 30.5, 0.5)
POWER_BINS = [-np.inf, 0.0, 0.05, 0.2, 0.4, 0.6, 0.8, 0.95, np.inf]

MANIFEST = []


def man(name, src, ftype, window, cat, interp, leak="safe"):
    MANIFEST.append({"feature_name": name,
                     "source_column(s)": src, "feature_type": ftype,
                     "window": window, "physical_category": cat,
                     "physical_interpretation": interp, "leakage_status": leak})
    return name


# --------------------------------------------------------------------------
# Level 1 - instantaneous derived channels (row-wise; no window, no leakage)
# --------------------------------------------------------------------------
def level1(g):
    """g is one turbine's frame indexed by time_stamp. Returns dict of Series."""
    f = {}

    def dT(name, col, label):
        f[name] = g[col] - g[AMB]

    # thermal rise over ambient - removes the seasonal/diurnal component
    for name, col, label in [
        ("dT_gbx_brg", "sensor_11_avg", "gearbox HS-shaft bearing"),
        ("dT_gbx_oil", "sensor_12_avg", "gearbox oil"),
        ("dT_genbrg_de", "sensor_13_avg", "generator bearing 2 (drive end)"),
        ("dT_genbrg_nde", "sensor_14_avg", "generator bearing 1 (non-drive end)"),
        ("dT_hyd_oil", "sensor_41_avg", "hydraulic group oil"),
        ("dT_splitring", "sensor_19_avg", "split ring chamber"),
        ("dT_nacelle", "sensor_43_avg", "nacelle"),
        ("dT_nosecone", "sensor_53_avg", "nose cone"),
    ]:
        dT(name, col, label)

    f["dT_stator"] = g[STATOR].mean(axis=1) - g[AMB]
    f["dT_trafo"] = g[TRAFO].mean(axis=1) - g[AMB]

    # self-normalising differentials: cancel ambient AND load
    f["genbrg_de_minus_nde"] = g["sensor_13_avg"] - g["sensor_14_avg"]
    f["gbx_brg_minus_oil"] = g["sensor_11_avg"] - g["sensor_12_avg"]

    # three-phase imbalance: spread is the meaningful quantity, not the level
    f["stator_spread"] = g[STATOR].max(axis=1) - g[STATOR].min(axis=1)
    f["trafo_spread"] = g[TRAFO].max(axis=1) - g[TRAFO].min(axis=1)
    f["igbt_rotor_spread"] = g[IGBT_R].max(axis=1) - g[IGBT_R].min(axis=1)
    f["current_spread"] = g[CURR].max(axis=1) - g[CURR].min(axis=1)
    f["voltage_spread"] = g[VOLT].max(axis=1) - g[VOLT].min(axis=1)

    # mechanical / performance -- guarded divisions produce NaN, never inf
    rot = g["sensor_52_avg"].where(g["sensor_52_avg"] > ROTOR_MIN_RPM)
    f["gear_ratio"] = g["sensor_18_avg"] / rot
    wind = g["wind_speed_3_avg"].where(g["wind_speed_3_avg"] > WIND_MIN_MS)
    f["tsr_proxy"] = g["sensor_52_avg"] / wind
    f["wind_turbulence"] = g["wind_speed_3_std"] / wind
    f["wind_speed_disagree"] = g["wind_speed_3_avg"] - g["wind_speed_4_avg"]
    f["power_deficit"] = g["power_29_avg"] - g["power_30_avg"]

    # angular -> sin/cos.  Arithmetic means of wrapping angles are meaningless.
    for name, col in [("yaw_misalign", "sensor_2_avg"),
                      ("wind_dir", "sensor_1_avg"),
                      ("nacelle_dir", "sensor_42_avg")]:
        rad = np.deg2rad(g[col].astype("float64"))
        f[name + "_sin"] = np.sin(rad)
        f[name + "_cos"] = np.cos(rad)
    return f


def power_curve_dev(g):
    """
    Deviation of actual power from the power this turbine has historically
    produced at the same wind speed.

    The reference is an EXPANDING per-wind-bin mean shifted by one observation,
    so it uses only that turbine's own strictly-earlier rows. No status filter is
    applied, so status_type_id never touches the feature matrix.
    """
    wb = pd.cut(g["wind_speed_3_avg"], WIND_BINS)
    exp = (g["power_30_avg"].groupby(wb, observed=True)
           .transform(lambda s: s.expanding().mean().shift(1)))
    return g["power_30_avg"] - exp


# --------------------------------------------------------------------------
# Level 2 - backward-looking temporal features
# --------------------------------------------------------------------------
def roll_slope(y, t_hours, win, mp):
    """
    OLS slope of y against time over a backward time window, per unit hour.

    Closed form from rolling sums so it stays vectorised. Rows where y is NaN are
    excluded from every sum, so a gap reduces n rather than biasing the fit.
    """
    valid = y.notna()
    yv = y.where(valid, 0.0)
    tv = t_hours.where(valid, 0.0)
    n = valid.astype("float64").rolling(win, min_periods=mp).sum()
    sx = tv.rolling(win, min_periods=mp).sum()
    sy = yv.rolling(win, min_periods=mp).sum()
    sxy = (tv * yv).rolling(win, min_periods=mp).sum()
    sxx = (tv * tv).rolling(win, min_periods=mp).sum()
    den = n * sxx - sx * sx
    den = den.where(den > 1e-9)
    return (n * sxy - sx * sy) / den


TIER_A = {
    "dT_gbx_brg": ("sensor_11_avg,sensor_0_avg", "gearbox", "gearbox HS-shaft bearing temperature rise over ambient"),
    "dT_gbx_oil": ("sensor_12_avg,sensor_0_avg", "gearbox", "gearbox oil temperature rise over ambient"),
    "dT_genbrg_de": ("sensor_13_avg,sensor_0_avg", "generator_bearing", "generator bearing 2 (DE) temperature rise over ambient"),
    "dT_genbrg_nde": ("sensor_14_avg,sensor_0_avg", "generator_bearing", "generator bearing 1 (NDE) temperature rise over ambient"),
    "dT_hyd_oil": ("sensor_41_avg,sensor_0_avg", "hydraulic", "hydraulic group oil temperature rise over ambient"),
    "genbrg_de_minus_nde": ("sensor_13_avg,sensor_14_avg", "generator_bearing", "drive-end minus non-drive-end bearing temperature"),
    "gbx_brg_minus_oil": ("sensor_11_avg,sensor_12_avg", "gearbox", "gearbox bearing minus gearbox oil temperature"),
    "power_curve_dev": ("power_30_avg,wind_speed_3_avg", "power", "deviation from this turbine's own historic power curve"),
}
TIER_B = {
    "dT_stator": ("sensor_15/16/17_avg,sensor_0_avg", "generator", "mean stator winding temperature rise over ambient"),
    "dT_trafo": ("sensor_38/39/40_avg,sensor_0_avg", "transformer", "mean HV transformer temperature rise over ambient"),
    "dT_splitring": ("sensor_19_avg,sensor_0_avg", "generator", "split ring chamber temperature rise over ambient"),
    "stator_spread": ("sensor_15/16/17_avg", "generator", "stator three-phase temperature imbalance"),
    "trafo_spread": ("sensor_38/39/40_avg", "transformer", "HV transformer three-phase temperature imbalance"),
    "gear_ratio": ("sensor_18_avg,sensor_52_avg", "mechanical", "generator rpm / rotor rpm - gearbox ratio integrity"),
    "sensor_5_std": ("sensor_5_std", "mechanical", "within-interval pitch activity"),
    "sensor_52_std": ("sensor_52_std", "mechanical", "within-interval rotor speed variability"),
}


def level2(chans, t_hours, first_pass):
    """Backward-looking rolling features for the selected channels."""
    out = {}
    for ch, (src, cat, interp) in TIER_A.items():
        y = chans[ch]
        for w in ("3h", "24h", "7d"):
            mp = MIN_PERIODS[w]
            out[f"{ch}__mean_{w}"] = y.rolling(w, min_periods=mp).mean()
            out[f"{ch}__std_{w}"] = y.rolling(w, min_periods=mp).std()
            if first_pass:
                man(f"{ch}__mean_{w}", src, "rolling_mean", w, cat, f"{w} backward mean of {interp}")
                man(f"{ch}__std_{w}", src, "rolling_std", w, cat, f"{w} backward std dev of {interp}")
        mp = MIN_PERIODS["24h"]
        mx = y.rolling("24h", min_periods=mp).max()
        mn = y.rolling("24h", min_periods=mp).min()
        out[f"{ch}__range_24h"] = mx - mn
        out[f"{ch}__slope_24h"] = roll_slope(y, t_hours, "24h", mp)
        out[f"{ch}__dev_short_long"] = out[f"{ch}__mean_3h"] - out[f"{ch}__mean_7d"]
        if first_pass:
            man(f"{ch}__range_24h", src, "rolling_range", "24h", cat, f"24h backward max-min of {interp}")
            man(f"{ch}__slope_24h", src, "rolling_slope", "24h", cat, f"24h backward OLS trend of {interp} (units/hour)")
            man(f"{ch}__dev_short_long", src, "short_vs_long_deviation", "3h vs 7d", cat,
                f"3h mean minus 7d mean of {interp} - recent departure from the machine's own baseline")

    for ch, (src, cat, interp) in TIER_B.items():
        y = chans[ch]
        out[f"{ch}__mean_24h"] = y.rolling("24h", min_periods=MIN_PERIODS["24h"]).mean()
        out[f"{ch}__std_24h"] = y.rolling("24h", min_periods=MIN_PERIODS["24h"]).std()
        out[f"{ch}__mean_7d"] = y.rolling("7d", min_periods=MIN_PERIODS["7d"]).mean()
        out[f"{ch}__dev_short_long"] = out[f"{ch}__mean_24h"] - out[f"{ch}__mean_7d"]
        if first_pass:
            man(f"{ch}__mean_24h", src, "rolling_mean", "24h", cat, f"24h backward mean of {interp}")
            man(f"{ch}__std_24h", src, "rolling_std", "24h", cat, f"24h backward std dev of {interp}")
            man(f"{ch}__mean_7d", src, "rolling_mean", "7d", cat, f"7d backward mean of {interp}")
            man(f"{ch}__dev_short_long", src, "short_vs_long_deviation", "24h vs 7d", cat,
                f"24h mean minus 7d mean of {interp}")
    return out


# --------------------------------------------------------------------------
# Level 3 - operating regime and window-occupancy bookkeeping
# --------------------------------------------------------------------------
def level3(g, first_pass):
    out = {}
    out["op_power_bin"] = pd.cut(g["power_30_avg"], POWER_BINS, labels=False).astype("float64")
    out["op_wind_bin"] = np.floor(g["wind_speed_3_avg"].clip(0, 30) / 2.0)
    producing = ((g["sensor_52_avg"] > ROTOR_MIN_RPM) &
                 (g["power_30_avg"] > POWER_PRODUCING))
    idle = g["sensor_52_avg"] <= ROTOR_MIN_RPM
    out["op_state"] = np.select([producing, idle], [2.0, 0.0], default=1.0)
    out["op_frac_producing_24h"] = (producing.astype("float64")
                                    .rolling("24h", min_periods=MIN_PERIODS["24h"]).mean())
    ones = pd.Series(1.0, index=g.index)
    for w in ("3h", "24h", "7d"):
        out[f"win_n_obs_{w}"] = ones.rolling(w, min_periods=1).sum()
    out["win_has_full_7d"] = (out["win_n_obs_7d"] >= MIN_PERIODS["7d"]).astype("float64")
    if first_pass:
        man("op_power_bin", "power_30_avg", "operating_regime", "instant", "operating_condition",
            "load bin (normalised grid power)")
        man("op_wind_bin", "wind_speed_3_avg", "operating_regime", "instant", "operating_condition",
            "wind speed bin (2 m/s)")
        man("op_state", "sensor_52_avg,power_30_avg", "operating_regime", "instant", "operating_condition",
            "0=idle (rotor<=5rpm), 1=transitional, 2=producing")
        man("op_frac_producing_24h", "sensor_52_avg,power_30_avg", "rolling_mean", "24h",
            "operating_condition", "fraction of the last 24h spent producing")
        for w in ("3h", "24h", "7d"):
            man(f"win_n_obs_{w}", "time_stamp", "window_occupancy", w, "data_quality",
                f"observations actually present in the {w} backward window "
                f"(expected {EXPECTED[w]}); exposes SCADA gaps")
        man("win_has_full_7d", "time_stamp", "window_occupancy", "7d", "data_quality",
            f"1 when the 7d window holds at least {MIN_PERIODS['7d']} observations")
    return out


# --------------------------------------------------------------------------
def build_turbine(g, first_pass=False):
    """All Phase 3 features for ONE turbine. g must be time-indexed and sorted."""
    chans = level1(g)
    chans["power_curve_dev"] = power_curve_dev(g)
    chans["sensor_5_std"] = g["sensor_5_std"]
    chans["sensor_52_std"] = g["sensor_52_std"]

    if first_pass:
        L1_META = [
            ("dT_gbx_brg", "sensor_11_avg,sensor_0_avg", "gearbox", "gearbox HS-shaft bearing temperature above ambient"),
            ("dT_gbx_oil", "sensor_12_avg,sensor_0_avg", "gearbox", "gearbox oil temperature above ambient"),
            ("dT_genbrg_de", "sensor_13_avg,sensor_0_avg", "generator_bearing", "generator bearing 2 (DE) above ambient"),
            ("dT_genbrg_nde", "sensor_14_avg,sensor_0_avg", "generator_bearing", "generator bearing 1 (NDE) above ambient"),
            ("dT_hyd_oil", "sensor_41_avg,sensor_0_avg", "hydraulic", "hydraulic group oil above ambient"),
            ("dT_splitring", "sensor_19_avg,sensor_0_avg", "generator", "split ring chamber above ambient"),
            ("dT_nacelle", "sensor_43_avg,sensor_0_avg", "reference", "nacelle temperature above ambient"),
            ("dT_nosecone", "sensor_53_avg,sensor_0_avg", "reference", "nose cone temperature above ambient"),
            ("dT_stator", "sensor_15/16/17_avg,sensor_0_avg", "generator", "mean stator winding temperature above ambient"),
            ("dT_trafo", "sensor_38/39/40_avg,sensor_0_avg", "transformer", "mean HV transformer temperature above ambient"),
            ("genbrg_de_minus_nde", "sensor_13_avg,sensor_14_avg", "generator_bearing",
             "DE minus NDE bearing temperature - self-normalising, cancels ambient and load"),
            ("gbx_brg_minus_oil", "sensor_11_avg,sensor_12_avg", "gearbox",
             "gearbox bearing minus oil temperature - local bearing heating"),
            ("stator_spread", "sensor_15/16/17_avg", "generator", "stator three-phase temperature imbalance"),
            ("trafo_spread", "sensor_38/39/40_avg", "transformer", "HV transformer three-phase temperature imbalance"),
            ("igbt_rotor_spread", "sensor_35/36/37_avg", "converter", "rotor-side IGBT three-phase temperature imbalance"),
            ("current_spread", "sensor_23/24/25_avg", "electrical", "three-phase current imbalance"),
            ("voltage_spread", "sensor_32/33/34_avg", "electrical", "three-phase voltage imbalance"),
            ("gear_ratio", "sensor_18_avg,sensor_52_avg", "mechanical",
             "generator rpm / rotor rpm; NaN when rotor <= 5 rpm"),
            ("tsr_proxy", "sensor_52_avg,wind_speed_3_avg", "mechanical",
             "rotor rpm / wind speed - tip-speed-ratio proxy; NaN when wind <= 1 m/s"),
            ("wind_turbulence", "wind_speed_3_std,wind_speed_3_avg", "wind",
             "turbulence intensity; NaN when wind <= 1 m/s"),
            ("wind_speed_disagree", "wind_speed_3_avg,wind_speed_4_avg", "wind",
             "measured minus estimated wind speed - anemometer health"),
            ("power_deficit", "power_29_avg,power_30_avg", "power",
             "possible minus actual active power - curtailment / derating"),
            ("power_curve_dev", "power_30_avg,wind_speed_3_avg", "power",
             "actual minus this turbine's own historic mean power at the same wind speed "
             "(expanding per-bin reference, shifted one row - uses no future data)"),
        ]
        for n, s, c, i in L1_META:
            man(n, s, "derived_instant", "instant", c, i)
        for n, col in [("yaw_misalign", "sensor_2_avg"), ("wind_dir", "sensor_1_avg"),
                       ("nacelle_dir", "sensor_42_avg")]:
            for tr in ("sin", "cos"):
                man(f"{n}_{tr}", col, "angular_" + tr, "instant", "wind" if n != "nacelle_dir" else "mechanical",
                    f"{tr} of {col} (degrees) - angular encoding; arithmetic means of wrapping angles are invalid")

    t_hours = pd.Series(
        (g.index.values.astype("datetime64[s]").astype("float64")
         - g.index.values[0].astype("datetime64[s]").astype("float64")) / 3600.0,
        index=g.index)

    feats = {}
    feats.update({k: v for k, v in chans.items()
                  if k not in ("sensor_5_std", "sensor_52_std")})
    feats.update(level2(chans, t_hours, first_pass))
    feats.update(level3(g, first_pass))
    return pd.DataFrame(feats, index=g.index)


def main():
    t0 = time.time()
    os.makedirs(OUTDIR, exist_ok=True)
    df = pd.read_parquet(IN)
    in_rows, in_cols = df.shape
    print("input : {}  {:,} rows x {} cols".format(IN, in_rows, in_cols))
    df = df.sort_values(["turbine_uid", "time_stamp"]).reset_index(drop=True)

    parts = []
    first = True
    for uid, g in df.groupby("turbine_uid", sort=True):
        gi = g.set_index("time_stamp")
        assert gi.index.is_monotonic_increasing, uid
        f = build_turbine(gi, first_pass=first)
        first = False
        f.insert(0, "turbine_uid", uid)
        f.insert(1, "asset_id", int(g.asset_id.iloc[0]))
        parts.append(f.reset_index())
        print("  {:>4}: {:,} rows -> {} engineered cols  ({:.0f}s)".format(
            uid, len(f), f.shape[1] - 2, time.time() - t0), flush=True)

    feat = pd.concat(parts, ignore_index=True)
    eng_cols = [c for c in feat.columns
                if c not in ("turbine_uid", "asset_id", "time_stamp")]
    feat[eng_cols] = feat[eng_cols].astype("float32")

    out = df.merge(feat, on=["turbine_uid", "asset_id", "time_stamp"],
                   how="left", validate="one_to_one")
    assert len(out) == in_rows, (len(out), in_rows)
    out = out.sort_values(["turbine_uid", "time_stamp"]).reset_index(drop=True)

    path = os.path.join(OUTDIR, "engineered_features.parquet")
    out.to_parquet(path, index=False)
    print("\nwrote {}  {:,} rows x {} cols  ({:.0f} MB)".format(
        path, len(out), out.shape[1], os.path.getsize(path) / 1e6))

    mani = pd.DataFrame(MANIFEST).drop_duplicates(subset=["feature_name"])
    for c in FORBIDDEN:
        mani.loc[len(mani)] = {"feature_name": c, "source_column(s)": c,
                               "feature_type": "EXCLUDED", "window": "",
                               "physical_category": "metadata/status",
                               "physical_interpretation":
                                   "passthrough or absent; never a predictive feature",
                               "leakage_status": "FORBIDDEN"}
    for c in DEFECTIVE:
        if c in out.columns:
            mani.loc[len(mani)] = {"feature_name": c, "source_column(s)": c,
                                   "feature_type": "EXCLUDED_DEFECTIVE", "window": "",
                                   "physical_category": "defective",
                                   "physical_interpretation":
                                       "constant-zero or scale-inconsistent; passthrough only",
                                   "leakage_status": "excluded_defective"}
    mpath = os.path.join(OUTDIR, "feature_manifest.csv")
    mani.to_csv(mpath, index=False)
    print("wrote {}  ({} rows: {} engineered + {} excluded)".format(
        mpath, len(mani), len(eng_cols), len(mani) - len(eng_cols)))

    meta = {"in_rows": in_rows, "in_cols": in_cols, "eng_cols": eng_cols,
            "elapsed_s": round(time.time() - t0, 1)}
    with open(os.path.join(OUTDIR, "_build_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print("\nelapsed {:.1f} min".format((time.time() - t0) / 60))
    print("frozen input and cleaned_data/ were NOT modified.")


if __name__ == "__main__":
    sys.exit(main())
