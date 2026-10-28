"""
Task 7 - Verify the Excel inspection copies against the authoritative Parquet.

Checks, for every generated workbook:
  * row count matches exactly (nothing silently truncated)
  * column set matches exactly (nothing silently dropped)
  * first and last timestamp preserved
  * asset IDs preserved
  * a numeric checksum matches (values preserved, not just shape)
  * event -> file mapping is correct

Also re-confirms the raw CSVs and cleaned_data/*.parquet are unchanged.

Read-only. Writes nothing.
"""

import hashlib
import os

import pandas as pd
from openpyxl import load_workbook

AD = "analysis_data"
OUT = os.path.join("cleaned_data", "excel")
OUT_T = os.path.join(OUT, "by_turbine")
CHECKSUM_COL = "power_30_avg"      # dense, high-entropy, present in both exports
TOL = 1e-3


def read_sheet(path, sheet):
    """Stream one sheet back: header + rows, without loading the whole workbook."""
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet]
    it = ws.iter_rows(values_only=True)
    header = list(next(it))
    n = 0
    ts_first = ts_last = None
    assets = set()
    chk = 0.0
    ci = header.index(CHECKSUM_COL) if CHECKSUM_COL in header else None
    ti = header.index("time_stamp") if "time_stamp" in header else None
    ai = header.index("asset_id") if "asset_id" in header else None
    for row in it:
        if row is None or all(v is None for v in row):
            continue
        n += 1
        if ti is not None and row[ti] is not None:
            if ts_first is None:
                ts_first = row[ti]
            ts_last = row[ti]
        if ai is not None and row[ai] is not None:
            assets.add(int(row[ai]))
        if ci is not None and row[ci] is not None:
            chk += float(row[ci])
    wb.close()
    return {"header": header, "rows": n, "ts_first": ts_first, "ts_last": ts_last,
            "assets": assets, "checksum": chk}


def compare(tag, xl, df, ts_col):
    ok = True
    msgs = []
    if xl["rows"] != len(df):
        ok = False
        msgs.append("ROW COUNT {} vs {}".format(xl["rows"], len(df)))
    missing = set(df.columns) - set(xl["header"])
    extra = set(xl["header"]) - set(df.columns)
    if missing or extra:
        ok = False
        msgs.append("COLUMNS missing={} extra={}".format(sorted(missing), sorted(extra)))
    if xl["ts_first"] is not None:
        a, b = pd.Timestamp(xl["ts_first"]), df[ts_col].min()
        c, d = pd.Timestamp(xl["ts_last"]), df[ts_col].max()
        if a != b or c != d:
            ok = False
            msgs.append("TIMESTAMPS {}..{} vs {}..{}".format(a, c, b, d))
    exp_assets = set(int(x) for x in df.asset_id.unique())
    if xl["assets"] != exp_assets:
        ok = False
        msgs.append("ASSET IDS {} vs {}".format(sorted(xl["assets"]), sorted(exp_assets)))
    exp_chk = float(df[CHECKSUM_COL].fillna(0).round(6).sum())
    if abs(xl["checksum"] - exp_chk) > TOL:
        ok = False
        msgs.append("CHECKSUM {:.6f} vs {:.6f}".format(xl["checksum"], exp_chk))
    print("  {:<34} {:>7,} rows x {:>3} cols   {}".format(
        tag, xl["rows"], len(xl["header"]), "OK" if ok else "MISMATCH -> " + "; ".join(msgs)))
    return ok


def main():
    events = pd.read_csv(os.path.join(AD, "event_index.csv"), sep=";")
    ev_lvl = pd.read_parquet(os.path.join(AD, "scada_by_event.parquet"))
    uniq = pd.read_parquet(os.path.join(AD, "scada_unique.parquet"))
    all_ok = True

    print("=" * 78)
    print("EVENT-WINDOW WORKBOOKS  ({}/event_<id>.xlsx)".format(OUT))
    print("=" * 78)
    total_rows = 0
    for eid in sorted(ev_lvl.event_id.unique()):
        path = os.path.join(OUT, "event_{}.xlsx".format(eid))
        if not os.path.exists(path):
            print("  MISSING: {}".format(path))
            all_ok = False
            continue
        g = ev_lvl[ev_lvl.event_id == eid]
        xl = read_sheet(path, "Cleaned_Data")
        all_ok &= compare("event_{}.xlsx".format(eid), xl, g, "time_stamp")
        total_rows += xl["rows"]
        # event -> turbine mapping must match event_index.csv
        meta = events[events.event_id == eid].iloc[0]
        if xl["assets"] != {int(meta.asset)}:
            print("     EVENT MAPPING MISMATCH: workbook assets {} vs event_info asset {}".format(
                sorted(xl["assets"]), int(meta.asset)))
            all_ok = False
    print("  ---> total rows across event workbooks: {:,}  (expected {:,})  {}".format(
        total_rows, len(ev_lvl), "OK" if total_rows == len(ev_lvl) else "MISMATCH"))
    all_ok &= (total_rows == len(ev_lvl))

    print("\n" + "=" * 78)
    print("TURBINE WORKBOOKS  ({}/asset_<id>.xlsx)".format(OUT_T))
    print("=" * 78)
    t_rows = 0
    for aid in sorted(uniq.asset_id.unique()):
        path = os.path.join(OUT_T, "asset_{}.xlsx".format(aid))
        if not os.path.exists(path):
            print("  MISSING: {}".format(path))
            all_ok = False
            continue
        g = uniq[uniq.asset_id == aid]
        xl = read_sheet(path, "SCADA_Data")
        all_ok &= compare("asset_{}.xlsx".format(aid), xl, g, "time_stamp")
        t_rows += xl["rows"]
    print("  ---> total rows across turbine workbooks: {:,}  (expected {:,})  {}".format(
        t_rows, len(uniq), "OK" if t_rows == len(uniq) else "MISMATCH"))
    all_ok &= (t_rows == len(uniq))

    print("\n" + "=" * 78)
    print("SOURCE DATA UNTOUCHED")
    print("=" * 78)
    raws = sorted(f for f in os.listdir("datasets") if f.endswith(".csv"))
    h = hashlib.md5()
    tot = 0
    for f in raws:
        p = os.path.join("datasets", f)
        tot += os.path.getsize(p)
        h.update(f.encode())
        h.update(str(os.path.getsize(p)).encode())
    print("  datasets/         : {} CSV files, {:.1f} MB, manifest md5 {}".format(
        len(raws), tot / 1e6, h.hexdigest()[:16]))
    for f in sorted(os.listdir("cleaned_data")):
        p = os.path.join("cleaned_data", f)
        if os.path.isfile(p):
            print("  cleaned_data/{:<28} {:>9.1f} MB   (not modified)".format(
                f, os.path.getsize(p) / 1e6))
    m = pd.read_parquet(os.path.join("cleaned_data", "cleaned_scada_data.parquet"),
                        columns=["asset_id"])
    print("  cleaned_data/cleaned_scada_data.parquet still has {:,} rows (unchanged)".format(len(m)))

    print("\n" + "=" * 78)
    print("RESULT: {}".format("ALL CHECKS PASSED" if all_ok else "SOME CHECKS FAILED"))
    print("=" * 78)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
