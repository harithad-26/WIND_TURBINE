"""
Phase 2 - Build corrected analysis base for Wind Farm A.

Rebuilds an analysis-ready dataset directly from the 22 raw event CSVs, fixing
three defects found in the Phase 1 master (cleaned_data/cleaned_scada_data.parquet):

  1. Each raw CSV is an EVENT WINDOW (filename == event_id), not a turbine.
     The Phase 1 concat discarded that provenance, so rows could not be traced
     back to an event and `event_info.csv` could not be joined.

  2. The Phase 1 drop_duplicates() included the per-file row counter `id`
     (which restarts at 0 in every file). That column is unique by
     construction, so it masked every duplicate: 64.47% of the Phase 1 master
     is repeated (asset_id, time_stamp) records.

  3. Two event files carry a TIMESTAMP OFFSET of exactly +1 day relative to the
     other files of the same turbine (event 40 on asset 10, event 71 on
     asset 0). Left uncorrected these look like two extra turbines; after
     correction they agree with their siblings on 100.000% of overlapping
     timestamps. The offset is detected empirically here, not hard-coded.

Reads   : datasets/*.csv  (read-only), event_info.csv
Writes  : analysis_data/*  (new directory; nothing existing is modified)

Neither datasets/ nor cleaned_data/ is written to by this script.
"""

import glob
import json
import os

import numpy as np
import pandas as pd

RAW_DIR = "datasets"
OUT_DIR = "analysis_data"
EVENT_INFO = "event_info.csv"

# High-entropy physical signals used to identify identical observations across
# event files. Two files from the same turbine, once aligned, agree on ~100% of
# overlapping timestamps; two different turbines agree on <0.1%.
FINGERPRINT = ["wind_speed_3_avg", "power_30_avg", "sensor_11_avg", "sensor_13_avg"]
MIN_MATCHES = 200        # minimum fingerprint matches to trust an offset
MIN_OVERLAP = 500        # minimum shared timestamps to verify a pair
SAME_TURBINE_PCT = 99.0  # agreement threshold for "same turbine"


def load_raw():
    """Load every raw event CSV, tagging each row with its source event_id."""
    frames = []
    paths = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")),
                   key=lambda p: int(os.path.basename(p)[:-4]))
    for path in paths:
        event_id = int(os.path.basename(path)[:-4])
        df = pd.read_csv(path, sep=";", parse_dates=["time_stamp"])
        df.insert(0, "event_id", event_id)
        # `id` is a per-file row counter that event_info indexes into; rename it
        # so it can never be mistaken for a global key or used as a feature.
        df.rename(columns={"id": "row_id_in_event"}, inplace=True)
        frames.append(df)
        print("  event {:>3}  asset {:>3}  {:>6} rows  {} .. {}".format(
            event_id, df.asset_id.iloc[0], len(df),
            df.time_stamp.min(), df.time_stamp.max()))
    return pd.concat(frames, ignore_index=True)


def detect_offsets(df):
    """
    Find each event file's timestamp offset relative to a reference file of the
    same asset_id, by taking the modal time-delta between rows whose sensor
    fingerprints match exactly.
    """
    fp = df.dropna(subset=FINGERPRINT)
    offsets, log = {}, []
    for aid, g in fp.groupby("asset_id"):
        evs = sorted(g.event_id.unique())
        ref = evs[0]
        R = g[g.event_id == ref].copy()
        R["k"] = list(zip(*[R[c] for c in FINGERPRINT]))
        R = R.drop_duplicates("k").set_index("k").time_stamp
        for e in evs:
            C = g[g.event_id == e].copy()
            C["k"] = list(zip(*[C[c] for c in FINGERPRINT]))
            C = C.drop_duplicates("k")
            matched = C.k.map(R)
            ok = matched.notna()
            if ok.sum() < MIN_MATCHES:
                offsets[e] = pd.Timedelta(0)
                log.append({"asset_id": int(aid), "ref_event": int(ref), "event_id": int(e),
                            "n_matched": int(ok.sum()), "offset": "0 days",
                            "pct_at_mode": None, "note": "too few matches; assumed 0"})
                continue
            delta = C.time_stamp[ok] - matched[ok]
            mode = delta.mode().iloc[0]
            offsets[e] = mode
            log.append({"asset_id": int(aid), "ref_event": int(ref), "event_id": int(e),
                        "n_matched": int(ok.sum()), "offset": str(mode),
                        "pct_at_mode": round(float((delta == mode).mean() * 100), 2),
                        "note": ""})
    return offsets, pd.DataFrame(log)


def verify_turbines(df, tcol):
    """Confirm that, after alignment, all files of an asset_id agree ~100%."""
    rows = []
    for aid, g in df.groupby("asset_id"):
        evs = sorted(g.event_id.unique())
        S = {e: g[g.event_id == e].set_index(tcol)[FINGERPRINT] for e in evs}
        for i, a in enumerate(evs):
            for b in evs[i + 1:]:
                idx = S[a].index.intersection(S[b].index)
                if len(idx) < MIN_OVERLAP:
                    continue
                xa, xb = S[a].loc[idx].to_numpy(), S[b].loc[idx].to_numpy()
                same = (xa == xb) | (np.isnan(xa) & np.isnan(xb))
                rows.append({"asset_id": int(aid), "event_a": int(a), "event_b": int(b),
                             "overlap": int(len(idx)),
                             "agree_pct": round(float(np.mean(np.all(same, axis=1)) * 100), 4)})
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=== 1. Loading 22 raw event CSVs ===")
    df = load_raw()
    print("\nTotal rows across event windows: {:,}  columns: {}".format(len(df), df.shape[1]))

    print("\n=== 2. Detecting per-file timestamp offsets ===")
    offsets, off_log = detect_offsets(df)
    print(off_log.to_string(index=False))
    df["time_offset_days"] = df.event_id.map(lambda e: offsets[e].total_seconds() / 86400)
    df["time_stamp_aligned"] = df.time_stamp - df.event_id.map(offsets)
    shifted = sorted(e for e, o in offsets.items() if o != pd.Timedelta(0))
    print("\n  Event files requiring a timestamp correction: {}".format(shifted or "none"))
    for e in shifted:
        print("    event {} : {} -> aligned by subtracting {}".format(e, offsets[e], offsets[e]))

    print("\n=== 3. Verifying turbine identity AFTER alignment ===")
    ver = verify_turbines(df, "time_stamp_aligned")
    ver.to_csv(os.path.join(AD_PAIRS := os.path.join(OUT_DIR, "turbine_agreement_pairs.csv")),
               index=False)
    bad = ver[ver.agree_pct < SAME_TURBINE_PCT]
    print("  file pairs compared: {}   min agreement: {:.4f}%".format(
        len(ver), ver.agree_pct.min()))
    print("  pairs below {}% agreement: {}".format(SAME_TURBINE_PCT, len(bad)))
    if len(bad):
        print(bad.to_string(index=False))
        raise SystemExit("Alignment failed - refusing to merge inconsistent files.")

    df["turbine_uid"] = "A" + df.asset_id.astype(str)
    print("  => {} physical turbines confirmed: {}".format(
        df.turbine_uid.nunique(), sorted(df.turbine_uid.unique())))

    print("\n=== 4. Column checks ===")
    const_zero = [c for c in df.columns
                  if c.startswith("sensor_") and df[c].notna().any()
                  and df[c].dropna().eq(0).all()]
    print("  Constant zero-valued sensor columns: {}".format(const_zero or "none"))
    miss = df.isna().sum()
    miss = miss[miss > 0]
    print("  Columns with missing values: {}".format(len(miss)))
    if not miss.empty:
        print(miss.to_string())

    # --- 5. Event-level table: every row kept, provenance intact -------------
    ev_path = os.path.join(OUT_DIR, "scada_by_event.parquet")
    df.to_parquet(ev_path, index=False)
    print("\n=== 5. Wrote {}  ({:,} rows x {} cols) ===".format(ev_path, len(df), df.shape[1]))

    # --- 6. Deduplicated per-turbine timeline -------------------------------
    # `train_test` is a property of an EVENT WINDOW, not of an observation
    # (the same timestamp is 'train' in one event and 'prediction' in another),
    # so it is deliberately NOT carried into the unique timeline.
    print("\n=== 6. Building deduplicated per-turbine timeline ===")
    drop = {"event_id", "row_id_in_event", "train_test", "turbine_uid",
            "asset_id", "time_stamp", "time_stamp_aligned", "time_offset_days"}
    sensor_cols = [c for c in df.columns if c not in drop]

    conflicts = int((df.groupby(["turbine_uid", "time_stamp_aligned"])[FINGERPRINT]
                       .nunique().gt(1).any(axis=1)).sum())
    st_conf = int((df.groupby(["turbine_uid", "time_stamp_aligned"])
                     .status_type_id.nunique() > 1).sum())
    print("  Sensor conflicts at same (turbine, aligned time): {}".format(conflicts))
    print("  status_type_id conflicts at same (turbine, aligned time): {}".format(st_conf))
    if conflicts or st_conf:
        raise SystemExit("Conflicting duplicates - refusing to deduplicate silently.")

    uniq = (df.sort_values(["turbine_uid", "time_stamp_aligned", "event_id"])
              .drop_duplicates(subset=["turbine_uid", "time_stamp_aligned"], keep="first")
              .drop(columns=["time_stamp"])            # native (possibly offset) time
              .rename(columns={"time_stamp_aligned": "time_stamp"})
              [["turbine_uid", "asset_id", "time_stamp"] + sensor_cols]
              .reset_index(drop=True))
    uq_path = os.path.join(OUT_DIR, "scada_unique.parquet")
    uniq.to_parquet(uq_path, index=False)
    print("  Wrote {}  ({:,} unique observations, {:,} duplicates removed = {:.2f}%)".format(
        uq_path, len(uniq), len(df) - len(uniq), (len(df) - len(uniq)) / len(df) * 100))

    # --- 7. Event index, with event times moved onto the aligned timeline ----
    ev = pd.read_csv(EVENT_INFO, sep=";", parse_dates=["event_start", "event_end"])
    ev["turbine_uid"] = "A" + ev.asset.astype(str)
    ev["time_offset_days"] = ev.event_id.map(lambda e: offsets[e].total_seconds() / 86400)
    ev["event_start_aligned"] = ev.event_start - ev.event_id.map(offsets)
    ev["event_end_aligned"] = ev.event_end - ev.event_id.map(offsets)
    win = df.groupby("event_id").time_stamp_aligned.agg(window_start="min", window_end="max")
    pred = (df[df.train_test == "prediction"].groupby("event_id").time_stamp_aligned
              .agg(pred_start="min", pred_end="max"))
    ev = ev.merge(win, on="event_id").merge(pred, on="event_id", how="left")
    ev["event_duration_h"] = (ev.event_end - ev.event_start).dt.total_seconds() / 3600
    ev.to_csv(os.path.join(OUT_DIR, "event_index.csv"), sep=";", index=False)
    print("\n=== 7. Wrote {}/event_index.csv  ({} events) ===".format(OUT_DIR, len(ev)))

    off_log.to_csv(os.path.join(OUT_DIR, "timestamp_offsets.csv"), index=False)

    # --- 8. Provenance manifest --------------------------------------------
    manifest = {
        "source_files": int(df.event_id.nunique()),
        "rows_event_level": int(len(df)),
        "rows_unique": int(len(uniq)),
        "duplicate_rows_removed": int(len(df) - len(uniq)),
        "duplicate_pct": round((len(df) - len(uniq)) / len(df) * 100, 4),
        "turbines": sorted(df.turbine_uid.unique()),
        "turbine_to_events": {u: sorted(int(e) for e in g.event_id.unique())
                              for u, g in df.groupby("turbine_uid")},
        "timestamp_offsets_applied": {str(e): str(o) for e, o in offsets.items()
                                      if o != pd.Timedelta(0)},
        "min_pairwise_agreement_pct_after_alignment": float(ver.agree_pct.min()),
        "constant_zero_columns": const_zero,
        "columns_with_missing": {k: int(v) for k, v in miss.items()},
        "aligned_time_range": [str(df.time_stamp_aligned.min()),
                               str(df.time_stamp_aligned.max())],
        "fingerprint_columns": FINGERPRINT,
    }
    with open(os.path.join(OUT_DIR, "analysis_base_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("=== 8. Wrote {}/analysis_base_manifest.json ===".format(OUT_DIR))
    print("\nDone. datasets/ and cleaned_data/ were not modified.")


if __name__ == "__main__":
    main()
