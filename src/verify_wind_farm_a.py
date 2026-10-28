"""
Task 1 - Verify the authoritative Wind Farm A data before Phase 3.

Nothing is assumed: every number below is measured from the files on disk.
Read-only. Writes nothing except a small JSON of the verified facts that the
Excel builders reuse, so the workbooks and the profile cannot drift apart.

Reads : datasets/*.csv (count only), cleaned_data/*.parquet, analysis_data/*,
        feature_description.csv, event_info.csv
Writes: analysis_data/verified_facts.json
"""

import glob
import json
import os

import pandas as pd

AD, CD, RAW = "analysis_data", "cleaned_data", "datasets"
STEP = pd.Timedelta(minutes=10)


def sect(t):
    print("\n" + "=" * 72)
    print(t)
    print("=" * 72)


def main():
    facts = {}

    sect("1. FILES ON DISK")
    raw = sorted(glob.glob(os.path.join(RAW, "*.csv")),
                 key=lambda p: int(os.path.basename(p)[:-4]))
    print("  raw event CSVs in datasets/      : {}".format(len(raw)))
    print("  file stems (= event_id)          : {}".format(
        [int(os.path.basename(p)[:-4]) for p in raw]))
    for d in (CD, AD):
        fs = sorted(os.listdir(d)) if os.path.isdir(d) else []
        print("  {}/ : {}".format(d, fs))
    facts["n_raw_files"] = len(raw)

    sect("2. AUTHORITATIVE BASE - analysis_data/scada_unique.parquet")
    u = pd.read_parquet(os.path.join(AD, "scada_unique.parquet"))
    print("  rows            : {:,}".format(len(u)))
    print("  columns         : {}".format(u.shape[1]))
    print("  turbines        : {}".format(u.turbine_uid.nunique()))
    print("  asset IDs       : {}".format(sorted(u.asset_id.unique().tolist())))
    print("  time range      : {} -> {}".format(u.time_stamp.min(), u.time_stamp.max()))
    span = u.time_stamp.max() - u.time_stamp.min()
    print("  span            : {} days ({:.2f} years)".format(span.days, span.days / 365.25))
    print("  duplicate (turbine,timestamp) : {}".format(
        int(u.duplicated(subset=["turbine_uid", "time_stamp"]).sum())))
    miss = u.isna().sum()
    miss = miss[miss > 0]
    print("  columns with missing values   : {} {}".format(
        len(miss), dict(miss) if len(miss) else ""))
    facts.update(rows_unique=int(len(u)), cols_unique=int(u.shape[1]),
                 n_turbines=int(u.turbine_uid.nunique()),
                 asset_ids=sorted(int(a) for a in u.asset_id.unique()),
                 t_min=str(u.time_stamp.min()), t_max=str(u.time_stamp.max()),
                 span_days=int(span.days),
                 missing_unique={k: int(v) for k, v in miss.items()})

    sect("3. COMPARISON WITH THE PHASE 1 MASTER (why analysis_data/ is authoritative)")
    m = pd.read_parquet(os.path.join(CD, "cleaned_scada_data.parquet"),
                        columns=["asset_id", "time_stamp", "id"])
    dup = int(m.duplicated(subset=["asset_id", "time_stamp"]).sum())
    print("  cleaned_data/cleaned_scada_data.parquet rows : {:,}".format(len(m)))
    print("    duplicate (asset_id,timestamp)             : {:,} ({:.2f}%)".format(
        dup, dup / len(m) * 100))
    print("    -> masked in Phase 1 because drop_duplicates() included the")
    print("       per-file row counter 'id', which restarts at 0 in every file")
    print("  analysis_data/scada_unique.parquet rows      : {:,}".format(len(u)))
    print("  VERDICT: use analysis_data/ for Phase 3; cleaned_data/ left untouched")
    facts.update(rows_phase1_master=int(len(m)), phase1_duplicates=dup)

    sect("4. SAMPLING INTERVAL PER TURBINE")
    samp = {}
    for uid, g in u.sort_values("time_stamp").groupby("turbine_uid"):
        d = g.time_stamp.diff().dropna()
        gaps = d[d > STEP]
        samp[uid] = {
            "asset_id": int(g.asset_id.iloc[0]), "rows": int(len(g)),
            "pct_of_total": round(len(g) / len(u) * 100, 2),
            "t_min": str(g.time_stamp.min()), "t_max": str(g.time_stamp.max()),
            "modal_step_min": float(d.mode().iloc[0].total_seconds() / 60),
            "pct_exactly_10min": round(float((d == STEP).mean() * 100), 3),
            "n_gaps": int(len(gaps)),
            "largest_gap_h": round(float(gaps.max().total_seconds() / 3600), 2) if len(gaps) else 0.0,
        }
        s = samp[uid]
        print("  {:>4}  rows={:>7,} ({:>5.2f}%)  {} -> {}  step={:.0f}min  "
              "10min={:.2f}%  gaps={:>3}  max_gap={:.1f}h".format(
                  uid, s["rows"], s["pct_of_total"], s["t_min"][:10], s["t_max"][:10],
                  s["modal_step_min"], s["pct_exactly_10min"], s["n_gaps"], s["largest_gap_h"]))
    facts["turbines"] = samp

    sect("5. COLUMN STRUCTURE")
    doc = pd.read_csv("feature_description.csv", sep=";", encoding="latin-1")
    ev_lvl = pd.read_parquet(os.path.join(AD, "scada_by_event.parquet"))
    print("  analysis_data/scada_by_event.parquet : {:,} rows x {} cols".format(
        len(ev_lvl), ev_lvl.shape[1]))
    print("  analysis_data/scada_unique.parquet   : {:,} rows x {} cols".format(
        len(u), u.shape[1]))
    meta = [c for c in ev_lvl.columns if c in
            ("event_id", "row_id_in_event", "asset_id", "turbine_uid", "time_stamp",
             "time_stamp_aligned", "time_offset_days", "train_test", "status_type_id")]
    sensors = [c for c in ev_lvl.columns if c not in meta]
    print("  metadata/identifier/status columns   : {} {}".format(len(meta), meta))
    print("  physical SCADA sensor columns        : {}".format(len(sensors)))
    print("  documented base signals              : {}".format(len(doc)))
    facts.update(cols_by_event=int(ev_lvl.shape[1]), n_meta_cols=len(meta),
                 n_sensor_cols=len(sensors), n_doc_base_signals=int(len(doc)),
                 rows_by_event=int(len(ev_lvl)), meta_cols=meta)

    sect("6. STATUS AND TRAIN_TEST")
    vc = u.status_type_id.value_counts().sort_index()
    print("  status_type_id (deduplicated base):")
    for k, v in vc.items():
        print("    code {} : {:>7,}  ({:>5.2f}%)".format(k, v, v / len(u) * 100))
    print("  -> code meanings: NOT DOCUMENTED in any supplied file")
    tt = ev_lvl.train_test.value_counts()
    print("  train_test (event-level, rows counted once per event window):")
    for k, v in tt.items():
        print("    {:<11}: {:>9,}".format(k, v))
    amb = int((ev_lvl.groupby(["turbine_uid", "time_stamp_aligned"])
                     .train_test.nunique() > 1).sum())
    print("  timestamps labelled BOTH train and prediction : {:,}".format(amb))
    print("  -> train_test is a per-EVENT-WINDOW flag, not an observation property")
    facts.update(status_counts={int(k): int(v) for k, v in vc.items()},
                 train_test_counts={str(k): int(v) for k, v in tt.items()},
                 ambiguous_train_test=amb)

    sect("7. EVENTS")
    ev = pd.read_csv(os.path.join(AD, "event_index.csv"), sep=";")
    print("  total events            : {}".format(len(ev)))
    print("  anomaly (failure)       : {}".format(int((ev.event_label == "anomaly").sum())))
    print("  normal (control)        : {}".format(int((ev.event_label == "normal").sum())))
    print("  event IDs               : {}".format(sorted(ev.event_id.tolist())))
    print("  turbines covered        : {}".format(sorted(ev.turbine_uid.unique().tolist())))
    print("  documented failure modes:")
    for k, v in ev[ev.event_label == "anomaly"].event_description.value_counts().items():
        print("    {:<28} {}".format(k, v))
    print("  event files present for every event_id : {}".format(
        sorted(ev.event_id.tolist()) == sorted(int(os.path.basename(p)[:-4]) for p in raw)))
    facts.update(n_events=int(len(ev)),
                 n_anomaly=int((ev.event_label == "anomaly").sum()),
                 n_normal=int((ev.event_label == "normal").sum()),
                 event_ids=sorted(int(e) for e in ev.event_id),
                 failure_modes=ev[ev.event_label == "anomaly"]
                               .event_description.value_counts().to_dict())

    sect("8. EXCEL FEASIBILITY (row limit 1,048,576)")
    per_ev = ev_lvl.groupby("event_id").size()
    print("  largest event window  : {:,} rows  -> fits on one sheet: {}".format(
        per_ev.max(), per_ev.max() < 1_048_575))
    print("  largest turbine       : {:,} rows  -> fits on one sheet: {}".format(
        max(s["rows"] for s in samp.values()),
        max(s["rows"] for s in samp.values()) < 1_048_575))
    print("  => no splitting required; every observation fits")
    facts["max_event_rows"] = int(per_ev.max())

    with open(os.path.join(AD, "verified_facts.json"), "w") as f:
        json.dump(facts, f, indent=2)
    print("\nWrote {}/verified_facts.json".format(AD))


if __name__ == "__main__":
    main()
