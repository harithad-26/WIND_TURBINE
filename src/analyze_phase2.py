"""
Phase 2 - Status / train_test / event analysis for Wind Farm A.

Computes the empirical evidence behind:
  reports/status_analysis.md
  reports/train_test_analysis.md
  reports/event_analysis.md

Reads : analysis_data/scada_by_event.parquet, analysis_data/scada_unique.parquet,
        analysis_data/event_index.csv
Writes: analysis_data/phase2_stats.json  (+ a few small CSVs)

No raw file and no file under cleaned_data/ is written.
"""

import json
import os

import numpy as np
import pandas as pd

AD = "analysis_data"
STEP = pd.Timedelta(minutes=10)


def runs(series):
    """Return run-length groups of consecutive equal values."""
    return (series != series.shift()).cumsum()


def main():
    uniq = pd.read_parquet(os.path.join(AD, "scada_unique.parquet"),
                           columns=["turbine_uid", "asset_id", "time_stamp",
                                    "status_type_id"])
    ev_lvl = pd.read_parquet(os.path.join(AD, "scada_by_event.parquet"),
                             columns=["event_id", "turbine_uid", "time_stamp_aligned",
                                      "train_test", "status_type_id"]
                             ).rename(columns={"time_stamp_aligned": "time_stamp"})
    events = pd.read_csv(os.path.join(AD, "event_index.csv"), sep=";",
                         parse_dates=["event_start", "event_end",
                                      "event_start_aligned", "event_end_aligned",
                                      "window_start", "window_end",
                                      "pred_start", "pred_end"])
    # Work on the aligned timeline throughout (events 40 and 71 carry a +1 day
    # native offset that build_analysis_base.py corrected).
    events["event_start"] = events["event_start_aligned"]
    events["event_end"] = events["event_end_aligned"]
    out = {}

    # ---------------------------------------------------------------- sampling
    print("=== Sampling regularity (unique timeline) ===")
    samp = {}
    for uid, g in uniq.sort_values("time_stamp").groupby("turbine_uid"):
        d = g.time_stamp.diff().dropna()
        vc = d.value_counts()
        gaps = d[d > STEP]
        samp[uid] = {
            "n_obs": int(len(g)),
            "t_min": str(g.time_stamp.min()),
            "t_max": str(g.time_stamp.max()),
            "pct_exactly_10min": round(float((d == STEP).mean() * 100), 3),
            "n_gaps_gt_10min": int(len(gaps)),
            "largest_gap_hours": round(float(gaps.max().total_seconds() / 3600), 2) if len(gaps) else 0.0,
            "total_missing_intervals": int(((d - STEP) / STEP).clip(lower=0).sum()),
            "modal_step_minutes": float(vc.index[0].total_seconds() / 60),
        }
        print("  {:>5} n={:>6} 10min={:>6.2f}%  gaps={:>4}  max_gap={:>7.2f}h".format(
            uid, samp[uid]["n_obs"], samp[uid]["pct_exactly_10min"],
            samp[uid]["n_gaps_gt_10min"], samp[uid]["largest_gap_hours"]))
    out["sampling"] = samp

    # ------------------------------------------------------------ status codes
    print("\n=== status_type_id (deduplicated timeline) ===")
    st = {}
    total = len(uniq)
    for code, g in uniq.groupby("status_type_id"):
        st[int(code)] = {
            "count": int(len(g)),
            "pct": round(float(len(g) / total * 100), 4),
            "turbines": sorted(g.turbine_uid.unique().tolist()),
            "n_turbines": int(g.turbine_uid.nunique()),
            "first_seen": str(g.time_stamp.min()),
            "last_seen": str(g.time_stamp.max()),
        }
    # run-length durations, computed per turbine on the ordered timeline
    dur = {c: [] for c in st}
    for uid, g in uniq.sort_values(["turbine_uid", "time_stamp"]).groupby("turbine_uid"):
        g = g.reset_index(drop=True)
        grp = runs(g.status_type_id)
        for _, blk in g.groupby(grp):
            dur[int(blk.status_type_id.iloc[0])].append(len(blk))
    for c, lens in dur.items():
        a = np.array(lens)
        st[c].update({
            "n_episodes": int(len(a)),
            "episode_min_minutes": int(a.min() * 10),
            "episode_max_minutes": int(a.max() * 10),
            "episode_mean_minutes": round(float(a.mean() * 10), 2),
            "episode_median_minutes": round(float(np.median(a) * 10), 2),
            "episode_p95_minutes": round(float(np.percentile(a, 95) * 10), 2),
        })
        print("  code {}: n={:>7} ({:>5.2f}%)  episodes={:>5}  mean={:>8.1f}min  max={:>9}min".format(
            c, st[c]["count"], st[c]["pct"], st[c]["n_episodes"],
            st[c]["episode_mean_minutes"], st[c]["episode_max_minutes"]))
    out["status"] = st

    # status x turbine
    ct = pd.crosstab(uniq.turbine_uid, uniq.status_type_id)
    ct.to_csv(os.path.join(AD, "status_by_turbine.csv"))
    out["status_by_turbine"] = ct.to_dict()
    print("\n  status count by turbine:\n", ct.to_string())
    ctp = (ct.T / ct.sum(axis=1) * 100).T.round(2)
    print("\n  status % by turbine:\n", ctp.to_string())
    out["status_pct_by_turbine"] = ctp.to_dict()

    # ------------------------------------------- status inside labelled events
    print("\n=== status_type_id inside labelled event periods ===")
    rows = []
    for _, e in events.iterrows():
        g = uniq[(uniq.turbine_uid == e.turbine_uid)
                 & (uniq.time_stamp >= e.event_start)
                 & (uniq.time_stamp <= e.event_end)]
        vc = g.status_type_id.value_counts()
        rows.append({
            "event_id": int(e.event_id), "turbine_uid": e.turbine_uid,
            "label": e.event_label,
            "description": e.event_description if isinstance(e.event_description, str) else "",
            "n_obs_in_event": int(len(g)),
            "pct_status_0": round(float(vc.get(0, 0) / len(g) * 100), 2) if len(g) else None,
            "pct_status_3": round(float(vc.get(3, 0) / len(g) * 100), 2) if len(g) else None,
            "pct_status_4": round(float(vc.get(4, 0) / len(g) * 100), 2) if len(g) else None,
        })
    ev_status = pd.DataFrame(rows)
    ev_status.to_csv(os.path.join(AD, "status_within_events.csv"), index=False)
    print(ev_status.to_string(index=False))
    out["status_within_events"] = ev_status.to_dict("records")

    print("\n  mean status share, anomaly vs normal events:")
    agg = ev_status.groupby("label")[["pct_status_0", "pct_status_3", "pct_status_4"]].mean().round(2)
    print(agg.to_string())
    out["status_share_by_label"] = agg.to_dict()

    # ------------------------------------------------------------- train_test
    print("\n=== train_test (per event window) ===")
    tt = []
    for eid, g in ev_lvl.groupby("event_id"):
        tr = g[g.train_test == "train"]
        pr = g[g.train_test == "prediction"]
        e = events[events.event_id == eid].iloc[0]
        tt.append({
            "event_id": int(eid), "turbine_uid": g.turbine_uid.iloc[0],
            "label": e.event_label,
            "n_train": int(len(tr)), "n_pred": int(len(pr)),
            "pct_pred": round(float(len(pr) / len(g) * 100), 2),
            "train_max": str(tr.time_stamp.max()) if len(tr) else None,
            "pred_min": str(pr.time_stamp.min()) if len(pr) else None,
            "pred_strictly_after_train": bool(len(pr) and len(tr)
                                              and pr.time_stamp.min() > tr.time_stamp.max()),
            "pred_covers_event": bool(len(pr)
                                      and pr.time_stamp.min() <= e.event_start
                                      and pr.time_stamp.max() >= e.event_end),
        })
    tt = pd.DataFrame(tt)
    tt.to_csv(os.path.join(AD, "train_test_by_event.csv"), index=False)
    print(tt.to_string(index=False))
    out["train_test_by_event"] = tt.to_dict("records")
    out["train_test_summary"] = {
        "all_pred_after_train": bool(tt.pred_strictly_after_train.all()),
        "all_pred_cover_event": bool(tt.pred_covers_event.all()),
        "n_events_with_both": int(((tt.n_train > 0) & (tt.n_pred > 0)).sum()),
        "total_train_rows": int(tt.n_train.sum()),
        "total_pred_rows": int(tt.n_pred.sum()),
    }
    print("\n  prediction strictly after train in every event: {}".format(
        out["train_test_summary"]["all_pred_after_train"]))
    print("  prediction window covers the labelled event in every event: {}".format(
        out["train_test_summary"]["all_pred_cover_event"]))

    # a timestamp can be 'train' in one event and 'prediction' in another
    lab = ev_lvl.groupby(["turbine_uid", "time_stamp"]).train_test.nunique()
    out["train_test_ambiguous_timestamps"] = int((lab > 1).sum())
    print("  timestamps labelled BOTH train and prediction (different events): {:,}".format(
        out["train_test_ambiguous_timestamps"]))

    # ----------------------------------------------------------------- events
    print("\n=== Events ===")
    events["n_obs_in_event"] = ev_status.n_obs_in_event.values
    ecols = ["event_id", "turbine_uid", "asset", "event_label", "event_description",
             "event_start", "event_end", "event_duration_h", "n_obs_in_event"]
    print(events[ecols].sort_values(["turbine_uid", "event_start"]).to_string(index=False))
    out["events"] = json.loads(events[ecols].to_json(orient="records", date_format="iso"))
    out["event_summary"] = {
        "n_events": int(len(events)),
        "n_anomaly": int((events.event_label == "anomaly").sum()),
        "n_normal": int((events.event_label == "normal").sum()),
        "failure_types": events[events.event_label == "anomaly"]
                         .event_description.value_counts().to_dict(),
        "anomalies_per_turbine": events[events.event_label == "anomaly"]
                                 .turbine_uid.value_counts().to_dict(),
        "duration_h": {
            "min": round(float(events.event_duration_h.min()), 2),
            "max": round(float(events.event_duration_h.max()), 2),
            "mean": round(float(events.event_duration_h.mean()), 2),
        },
    }
    print("\n  failure types:", out["event_summary"]["failure_types"])
    print("  anomalies per turbine:", out["event_summary"]["anomalies_per_turbine"])

    with open(os.path.join(AD, "phase2_stats.json"), "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("\nWrote {}/phase2_stats.json".format(AD))


if __name__ == "__main__":
    main()
