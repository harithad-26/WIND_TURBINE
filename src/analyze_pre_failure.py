"""
Phase 2 - Exploratory pre-event SCADA behaviour for Wind Farm A.

Question: does sensor behaviour change BEFORE a documented anomaly, and does it
do so more than before a documented *normal* event?

Design notes (why it is built this way):
  * The 10 `normal` events act as a CONTROL GROUP. Any drift claimed for
    anomalies must be absent (or much weaker) in normals, otherwise it is a
    seasonal//operational artefact rather than a fault precursor.
  * Only status_type_id == 0 observations are used in the pre-windows and the
    baseline. Status 4 dominates the event period itself (95% of anomaly-event
    observations), so including it would simply re-detect the shutdown, not a
    precursor.
  * Turbine temperatures depend strongly on load. Raw temperature deltas are
    therefore reported alongside POWER-BINNED RESIDUALS: the sensor value minus
    the baseline mean for the same turbine in the same power bin.

This is exploratory only. No target is created and no feature is selected.

Reads : analysis_data/scada_unique.parquet, analysis_data/event_index.csv
Writes: analysis_data/pre_event_*.csv, analysis_data/status_onset.csv
"""

import os

import numpy as np
import pandas as pd

AD = "analysis_data"

# Documented sensors most relevant to the failure types present in event_info.
SENSORS = {
    "sensor_11_avg": "Gearbox bearing temp (high speed shaft)",
    "sensor_12_avg": "Gearbox oil temp",
    "sensor_13_avg": "Generator bearing 2 temp (Drive End)",
    "sensor_14_avg": "Generator bearing 1 temp (Non-Drive End)",
    "sensor_15_avg": "Stator winding temp phase 1",
    "sensor_16_avg": "Stator winding temp phase 2",
    "sensor_17_avg": "Stator winding temp phase 3",
    "sensor_38_avg": "HV transformer temp L1",
    "sensor_39_avg": "HV transformer temp L2",
    "sensor_40_avg": "HV transformer temp L3",
    "sensor_41_avg": "Hydraulic group oil temp",
    "sensor_43_avg": "Nacelle temp",
    "sensor_19_avg": "Split ring chamber temp",
    "sensor_53_avg": "Nose cone temp",
    "power_30_avg": "Grid power",
    "sensor_18_avg": "Generator rpm",
    "sensor_52_avg": "Rotor rpm",
    "sensor_5_std": "Pitch angle std dev",
    "wind_speed_3_avg": "Wind speed",
    "sensor_0_avg": "Ambient temp",
}

WINDOWS_H = [1, 6, 12, 24, 72, 168]          # 1h .. 7d before event_start
BASE_FROM_D, BASE_TO_D = 90, 30              # baseline: 90d..30d before event
POWER_BINS = [-np.inf, 0, 100, 300, 600, 1000, 1500, np.inf]


def main():
    cols = ["turbine_uid", "time_stamp", "status_type_id"] + list(SENSORS)
    df = pd.read_parquet(os.path.join(AD, "scada_unique.parquet"), columns=cols)
    events = pd.read_csv(os.path.join(AD, "event_index.csv"), sep=";",
                         parse_dates=["event_start_aligned", "event_end_aligned"])
    # aligned timeline (events 40 and 71 carry a +1 day native offset)
    events["event_start"] = events["event_start_aligned"]
    events["event_end"] = events["event_end_aligned"]

    # ---------------------------------------------- status onset vs event start
    print("=== How far BEFORE event_start does status_type_id leave 0? ===")
    onset = []
    for _, e in events.iterrows():
        g = df[(df.turbine_uid == e.turbine_uid)
               & (df.time_stamp >= e.event_start - pd.Timedelta(days=14))
               & (df.time_stamp <= e.event_start)].sort_values("time_stamp")
        nz = g[g.status_type_id != 0]
        # last contiguous non-zero block running up to event_start
        lead = np.nan
        if len(g) and g.status_type_id.iloc[-1] != 0:
            blk = (g.status_type_id != 0).values
            i = len(blk) - 1
            while i >= 0 and blk[i]:
                i -= 1
            lead = (e.event_start - g.time_stamp.iloc[i + 1]).total_seconds() / 3600
        onset.append({
            "event_id": int(e.event_id), "turbine_uid": e.turbine_uid,
            "label": e.event_label,
            "description": e.event_description if isinstance(e.event_description, str) else "",
            "status_at_event_start": int(g.status_type_id.iloc[-1]) if len(g) else None,
            "nonzero_lead_hours": round(lead, 2) if lead == lead else 0.0,
            "pct_nonzero_prev_14d": round(float((nz.shape[0] / len(g)) * 100), 2) if len(g) else None,
        })
    onset = pd.DataFrame(onset)
    onset.to_csv(os.path.join(AD, "status_onset.csv"), index=False)
    print(onset.to_string(index=False))

    # ------------------------------------------------ pre-window vs baseline
    print("\n=== Pre-event drift vs 90d-30d baseline (status 0 only) ===")
    recs = []
    for _, e in events.iterrows():
        g = df[df.turbine_uid == e.turbine_uid]
        base = g[(g.time_stamp >= e.event_start - pd.Timedelta(days=BASE_FROM_D))
                 & (g.time_stamp < e.event_start - pd.Timedelta(days=BASE_TO_D))
                 & (g.status_type_id == 0)]
        if len(base) < 500:
            print("  event {} skipped: baseline only {} rows".format(e.event_id, len(base)))
            continue
        base = base.copy()
        base["pbin"] = pd.cut(base.power_30_avg, POWER_BINS)
        bmean = base.groupby("pbin", observed=False)[list(SENSORS)].mean()
        bstd = base[list(SENSORS)].std()

        for h in WINDOWS_H:
            w = g[(g.time_stamp >= e.event_start - pd.Timedelta(hours=h))
                  & (g.time_stamp < e.event_start) & (g.status_type_id == 0)]
            if len(w) < 3:
                continue
            w = w.copy()
            w["pbin"] = pd.cut(w.power_30_avg, POWER_BINS)
            row = {"event_id": int(e.event_id), "turbine_uid": e.turbine_uid,
                   "label": e.event_label,
                   "description": e.event_description if isinstance(e.event_description, str) else "",
                   "window_h": h, "n_obs": int(len(w))}
            for s in SENSORS:
                raw = w[s].mean() - base[s].mean()
                # power-binned residual: compare like-for-like load conditions
                exp = w.pbin.map(bmean[s])
                resid = (w[s] - exp).mean()
                row["raw_" + s] = round(float(raw), 3) if raw == raw else None
                row["resid_" + s] = round(float(resid), 3) if resid == resid else None
                row["z_" + s] = (round(float(resid / bstd[s]), 3)
                                 if bstd[s] and bstd[s] > 0 and resid == resid else None)
            recs.append(row)

    pre = pd.DataFrame(recs)
    pre.to_csv(os.path.join(AD, "pre_event_drift.csv"), index=False)
    print("  computed {} event x window rows".format(len(pre)))

    # ---------------------------------- anomaly vs normal: mean |z| comparison
    print("\n=== Power-binned residual z-score: anomaly vs normal control ===")
    zc = [c for c in pre.columns if c.startswith("z_")]
    summ = pre.groupby(["label", "window_h"])[zc].mean().round(3)
    for h in WINDOWS_H:
        if h not in pre.window_h.values:
            continue
        print("\n  --- {}h before event ---".format(h))
        t = pd.DataFrame({
            "anomaly_z": summ.loc[("anomaly", h)] if ("anomaly", h) in summ.index else np.nan,
            "normal_z": summ.loc[("normal", h)] if ("normal", h) in summ.index else np.nan,
        })
        t.index = [i[2:] for i in t.index]
        t["|diff|"] = (t.anomaly_z - t.normal_z).abs().round(3)
        t["description"] = [SENSORS[i] for i in t.index]
        print(t.sort_values("|diff|", ascending=False).head(12).to_string())
    summ.to_csv(os.path.join(AD, "pre_event_z_by_label.csv"))

    # ------------------------------- per-failure-type view at the 24h horizon
    print("\n=== Per-event residual z at 24h before event_start (top sensor each) ===")
    w24 = pre[pre.window_h == 24]
    for _, r in w24.iterrows():
        zs = {c[2:]: r[c] for c in zc if r[c] == r[c]}
        if not zs:
            continue
        top = sorted(zs.items(), key=lambda kv: -abs(kv[1]))[:3]
        print("  ev{:>3} {:>5} {:>7} {:<26} -> ".format(
            r.event_id, r.turbine_uid, r.label, r.description[:26])
            + ", ".join("{}={:+.2f}".format(k, v) for k, v in top))

    print("\nWrote {}/pre_event_drift.csv, pre_event_z_by_label.csv, status_onset.csv".format(AD))


if __name__ == "__main__":
    main()
