"""
Tasks 3 & 4 - Human-readable Excel inspection copies of the cleaned Wind Farm A data.

  cleaned_data/excel/event_<id>.xlsx        one file per EVENT WINDOW (22)
  cleaned_data/excel/by_turbine/asset_<id>.xlsx   one file per TURBINE (5)

Source of truth:
  event files   <- analysis_data/scada_by_event.parquet   (provenance intact)
  turbine files <- analysis_data/scada_unique.parquet     (deduplicated)

NOT cleaned_data/cleaned_scada_data.parquet - that master contains 64.47%
duplicate (asset_id, time_stamp) records. It is left completely untouched.

IMPORTANT: datasets/72.csv is EVENT 72, not turbine 72. The filename is an
event_id. That mapping is verified, never assumed.

These workbooks are INSPECTION COPIES ONLY. The ML pipeline keeps using Parquet.

Writes only under cleaned_data/excel/. No raw file, no Parquet, no report is modified.
"""

import json
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from excel_utils import new_workbook, write_kv_sheet, write_table_sheet, finalize  # noqa: E402

AD = "analysis_data"
OUT = os.path.join("cleaned_data", "excel")
OUT_T = os.path.join(OUT, "by_turbine")
STEP = pd.Timedelta(minutes=10)

# Column order for the event workbooks: identity and metadata first, sensors after.
EVENT_LEAD = ["event_id", "row_id_in_event", "time_stamp", "time_stamp_aligned",
              "time_offset_days", "asset_id", "turbine_uid", "train_test",
              "status_type_id"]
TURBINE_LEAD = ["turbine_uid", "asset_id", "time_stamp", "status_type_id"]


def order(df, lead):
    lead = [c for c in lead if c in df.columns]
    return df[lead + [c for c in df.columns if c not in lead]]


def build_event_files(ev_lvl, events, manifest):
    os.makedirs(OUT, exist_ok=True)
    rows = []
    ids = sorted(ev_lvl.event_id.unique())
    for k, eid in enumerate(ids, start=1):
        t0 = time.time()
        g = order(ev_lvl[ev_lvl.event_id == eid].copy(), EVENT_LEAD)
        g = g.sort_values("time_stamp_aligned").reset_index(drop=True)
        meta = events[events.event_id == eid].iloc[0]

        wb = new_workbook()
        write_table_sheet(wb, g, "Cleaned_Data")

        desc = meta.event_description if isinstance(meta.event_description, str) else ""
        off = float(manifest["turbine_to_events"] and 0) or 0.0
        offset_note = str(g.time_offset_days.iloc[0])
        info = [
            ("-- EVENT --", ""),
            ("event_id", int(eid)),
            ("source raw file", "datasets/{}.csv".format(eid)),
            ("event_label", meta.event_label),
            ("event_description", desc or "(empty - this is a NORMAL control window)"),
            ("turbine (derived)", meta.turbine_uid),
            ("asset_id (raw field)", int(meta.asset)),
            ("-- TIMING (native file timestamps) --", ""),
            ("event_start", str(meta.event_start)),
            ("event_end", str(meta.event_end)),
            ("event_duration_hours", round(float(meta.event_duration_h), 2)),
            ("event_start_id (index into row_id_in_event)", int(meta.event_start_id)),
            ("event_end_id (index into row_id_in_event)", int(meta.event_end_id)),
            ("-- TIMING (aligned timeline) --", ""),
            ("timestamp offset applied (days)", offset_note),
            ("event_start_aligned", str(meta.event_start_aligned)),
            ("event_end_aligned", str(meta.event_end_aligned)),
            ("-- THIS WINDOW --", ""),
            ("rows in this event window", int(len(g))),
            ("window start (aligned)", str(g.time_stamp_aligned.min())),
            ("window end (aligned)", str(g.time_stamp_aligned.max())),
            ("train rows", int((g.train_test == "train").sum())),
            ("prediction rows", int((g.train_test == "prediction").sum())),
            ("status 0 / 3 / 4 rows", "{} / {} / {}".format(
                int((g.status_type_id == 0).sum()), int((g.status_type_id == 3).sum()),
                int((g.status_type_id == 4).sum()))),
            ("-- NOTES --", ""),
            ("File naming", "The number is an EVENT ID, not a turbine ID."),
            ("row_id_in_event", "Per-file row counter restarting at 0. event_info "
                                "indexes into it. Never use as an ML feature."),
            ("time_stamp vs time_stamp_aligned",
             "Events 40 and 71 carry a +1 day offset in their native timestamps. "
             "time_stamp_aligned puts every file on one common timeline."),
            ("train_test", "A property of THIS event window only. The same timestamp "
                           "is 'train' in one event file and 'prediction' in another."),
            ("status_type_id", "Code meanings are NOT DOCUMENTED. Not a failure label."),
            ("Purpose", "Human inspection copy. Authoritative data is "
                        "analysis_data/scada_by_event.parquet."),
        ]
        write_kv_sheet(wb, info, "Event_Info", col_widths=(48, 78))
        path = os.path.join(OUT, "event_{}.xlsx".format(eid))
        finalize(wb, path)
        sz = os.path.getsize(path) / 1e6
        rows.append({"event_id": int(eid), "file": os.path.basename(path),
                     "rows": int(len(g)), "cols": int(g.shape[1]), "mb": round(sz, 1)})
        print("  [{:>2}/{}] event_{}.xlsx  {:,} rows x {} cols  {:.1f} MB  ({:.0f}s)".format(
            k, len(ids), eid, len(g), g.shape[1], sz, time.time() - t0), flush=True)
    return pd.DataFrame(rows)


def build_turbine_files(uniq, ev_lvl, events):
    os.makedirs(OUT_T, exist_ok=True)
    rows = []
    uids = sorted(uniq.turbine_uid.unique())
    for k, uid in enumerate(uids, start=1):
        t0 = time.time()
        g = order(uniq[uniq.turbine_uid == uid].copy(), TURBINE_LEAD)
        g = g.sort_values("time_stamp").reset_index(drop=True)
        aid = int(g.asset_id.iloc[0])

        d = g.time_stamp.diff().dropna()
        gaps = d[d > STEP]
        miss = g.isna().sum()
        miss = miss[miss > 0]
        st = g.status_type_id.value_counts().sort_index()
        # train_test lives at event level only - report it there, honestly.
        evs = sorted(events[events.turbine_uid == uid].event_id.tolist())
        sub = ev_lvl[ev_lvl.turbine_uid == uid]
        n_sensor = len([c for c in g.columns if c not in TURBINE_LEAD])

        wb = new_workbook()
        write_table_sheet(wb, g, "SCADA_Data")
        info = [
            ("-- TURBINE --", ""),
            ("turbine_uid (derived)", uid),
            ("asset_id (raw field)", aid),
            ("-- SIZE --", ""),
            ("row count (deduplicated observations)", int(len(g))),
            ("share of Wind Farm A", "{:.2f}%".format(len(g) / 425023 * 100)),
            ("total columns", int(g.shape[1])),
            ("physical SCADA sensor columns", n_sensor),
            ("-- TIME --", ""),
            ("first timestamp", str(g.time_stamp.min())),
            ("last timestamp", str(g.time_stamp.max())),
            ("span (days)", int((g.time_stamp.max() - g.time_stamp.min()).days)),
            ("sampling interval (modal)", "{:.0f} minutes".format(
                d.mode().iloc[0].total_seconds() / 60)),
            ("intervals exactly 10 minutes", "{:.3f}%".format(float((d == STEP).mean() * 100))),
            ("gaps longer than 10 minutes", int(len(gaps))),
            ("largest gap (hours)", round(float(gaps.max().total_seconds() / 3600), 2)
             if len(gaps) else 0.0),
            ("-- MISSING VALUES --", ""),
            ("columns with missing values", int(len(miss))),
            ("detail", ", ".join("{}={}".format(a, b) for a, b in miss.items()) or "none"),
            ("-- STATUS DISTRIBUTION --", ""),
        ]
        for code in (0, 3, 4):
            n = int(st.get(code, 0))
            info.append(("status_type_id == {}".format(code),
                         "{:,}  ({:.2f}%)".format(n, n / len(g) * 100)))
        info += [
            ("status code meanings", "NOT DOCUMENTED in any supplied file"),
            ("-- EVENTS ON THIS TURBINE --", ""),
            ("event windows", ", ".join(str(e) for e in evs)),
            ("anomaly events", int(((events.turbine_uid == uid) &
                                    (events.event_label == "anomaly")).sum())),
            ("normal (control) events", int(((events.turbine_uid == uid) &
                                             (events.event_label == "normal")).sum())),
            ("documented failure modes", "; ".join(
                events[(events.turbine_uid == uid) & (events.event_label == "anomaly")]
                .event_description.dropna().tolist()) or "none"),
            ("-- TRAIN / PREDICTION --", ""),
            ("train rows (summed over this turbine's event windows)",
             int((sub.train_test == "train").sum())),
            ("prediction rows (summed over its event windows)",
             int((sub.train_test == "prediction").sum())),
            ("why it is not a column in SCADA_Data",
             "train_test belongs to an EVENT WINDOW, not to an observation. Because "
             "windows overlap, the same timestamp is 'train' in one event and "
             "'prediction' in another, so it cannot be assigned to a deduplicated "
             "row. See the event_*.xlsx files for the per-window flag."),
            ("-- NOTES --", ""),
            ("Purpose", "Human inspection copy. Authoritative data is "
                        "analysis_data/scada_unique.parquet."),
            ("Deduplication", "One row per (turbine, aligned timestamp). The Phase 1 "
                              "master repeated most observations up to 5 times."),
        ]
        write_kv_sheet(wb, info, "Summary", col_widths=(52, 74))
        path = os.path.join(OUT_T, "asset_{}.xlsx".format(aid))
        finalize(wb, path)
        sz = os.path.getsize(path) / 1e6
        rows.append({"turbine_uid": uid, "asset_id": aid,
                     "file": os.path.basename(path), "rows": int(len(g)),
                     "cols": int(g.shape[1]), "mb": round(sz, 1)})
        print("  [{}/{}] asset_{}.xlsx  {:,} rows x {} cols  {:.1f} MB  ({:.0f}s)".format(
            k, len(uids), aid, len(g), g.shape[1], sz, time.time() - t0), flush=True)
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    manifest = json.load(open(os.path.join(AD, "analysis_base_manifest.json")))
    events = pd.read_csv(os.path.join(AD, "event_index.csv"), sep=";",
                         parse_dates=["event_start", "event_end",
                                      "event_start_aligned", "event_end_aligned"])
    ev_lvl = pd.read_parquet(os.path.join(AD, "scada_by_event.parquet"))
    uniq = pd.read_parquet(os.path.join(AD, "scada_unique.parquet"))

    print("=== TASK 3: event-window Excel files -> {}/ ===".format(OUT), flush=True)
    a = build_event_files(ev_lvl, events, manifest)
    print("\n=== TASK 4: per-turbine Excel files -> {}/ ===".format(OUT_T), flush=True)
    b = build_turbine_files(uniq, ev_lvl, events)

    a.to_csv(os.path.join(AD, "excel_event_files.csv"), index=False)
    b.to_csv(os.path.join(AD, "excel_turbine_files.csv"), index=False)
    print("\nEvent files : {}  rows total {:,}  ({:.0f} MB)".format(
        len(a), a.rows.sum(), a.mb.sum()))
    print("Turbine files: {}  rows total {:,}  ({:.0f} MB)".format(
        len(b), b.rows.sum(), b.mb.sum()))
    print("Total elapsed: {:.1f} min".format((time.time() - t0) / 60))
    print("Raw files and cleaned_data/*.parquet were NOT modified.")


if __name__ == "__main__":
    main()
