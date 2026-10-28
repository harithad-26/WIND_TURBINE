"""
Phase 2 / Task 1 - Build reports/sensor_mapping_report.md.

Cross-checks every column of the analysis base against feature_description.csv.
Descriptions and units are copied VERBATIM from the documentation; any column the
documentation does not cover is written as "Not documented." Nothing is inferred.

Reads : analysis_data/scada_unique.parquet, feature_description.csv
Writes: reports/sensor_mapping_report.md, analysis_data/sensor_mapping.csv
"""

import os
import re

import pandas as pd

AD, REP = "analysis_data", "reports"

# Category is assigned ONLY from the documented description text, by keyword.
# A column whose description is not documented gets "Not documented."
CATEGORY_RULES = [
    (r"temperature|temp\b", "Temperature"),
    (r"rpm", "Rotational speed"),
    (r"wind ?speed", "Wind"),
    (r"wind .*direction|nacelle direction", "Wind / orientation"),
    (r"pitch", "Pitch"),
    (r"reactive power", "Electrical - reactive power"),
    (r"active power|grid power", "Electrical - active power"),
    (r"current", "Electrical - current"),
    (r"voltage", "Electrical - voltage"),
    (r"frequency", "Electrical - grid"),
    (r"phase displacement", "Electrical - power factor"),
]

ROLE_OVERRIDES = {
    "time_stamp": ("Identifier / time", "Timestamp of the 10-minute aggregation interval",
                   "datetime", "Indexing and time-based splitting only. Never a feature."),
    "asset_id": ("Identifier", "Turbine identifier as supplied in the raw files",
                 "int", "Grouping key. NOT globally unique on its own - see turbine_uid."),
    "turbine_uid": ("Identifier", "Turbine identifier derived in this project",
                    "string", "Grouping key for per-turbine analysis and splitting."),
    "event_id": ("Metadata / provenance", "Source event-window file (filename == event_id)",
                 "int", "Provenance and event-level evaluation. Never a feature."),
    "row_id_in_event": ("Metadata / provenance",
                        "Per-file row counter; event_info.csv indexes into it",
                        "int", "Joins event_info to rows. MUST NOT be used as a feature."),
    "train_test": ("Metadata", "Benchmark split flag of the source event window",
                   "string", "Per-event-window metadata, not an observation property."),
    "status_type_id": ("Status", "Operating-status code", "int",
                       "Meaning NOT documented in the supplied files. Near-perfect "
                       "proxy for the event label - severe leakage risk."),
}


def base_and_stat(col):
    """Split e.g. 'wind_speed_3_max' into ('wind_speed_3', 'max')."""
    m = re.match(r"^(.*?)_(avg|max|min|std)$", col)
    return (m.group(1), {"avg": "average", "max": "maximum",
                         "min": "minimum", "std": "std_dev"}[m.group(2)]) if m else (col, "value")


def categorise(desc):
    low = desc.lower()
    for pat, cat in CATEGORY_RULES:
        if re.search(pat, low):
            return cat
    return "Other (documented)"


def main():
    # feature_description.csv is valid UTF-8, but the degree sign was already lost
    # upstream: the file literally contains U+FFFD (29 of them). Map it to "deg".
    doc = pd.read_csv("feature_description.csv", sep=";", encoding="utf-8")
    doc["unit"] = (doc.unit.fillna("").astype(str)
                   .str.replace("�", "deg", regex=False)
                   .str.replace("°", "deg", regex=False))
    D = doc.set_index("sensor_name")

    df = pd.read_parquet(os.path.join(AD, "scada_unique.parquet"))
    rows = []
    for c in df.columns:
        s = df[c]
        base, stat = base_and_stat(c)
        if c in ROLE_OVERRIDES:
            role, desc, unit, rel = ROLE_OVERRIDES[c]
            cat = role
        elif base in D.index:
            desc = str(D.loc[base, "description"])
            unit = str(D.loc[base, "unit"]) or "(none given)"
            cat = categorise(desc)
            role = "Physical measurement"
            rel = ""
        else:
            desc = unit = "Not documented."
            cat = "Not documented."
            role = "Not documented."
            rel = "Cannot be justified physically; exclude until documented."
        num = pd.api.types.is_numeric_dtype(s)
        rows.append({
            "column": c, "base_signal": base, "statistic": stat,
            "documented_description": desc, "unit": unit,
            "category": cat, "role": role,
            "dtype": str(s.dtype),
            "n_missing": int(s.isna().sum()),
            "pct_missing": round(float(s.isna().mean() * 100), 4),
            "n_unique": int(s.nunique(dropna=True)),
            "min": round(float(s.min()), 3) if num else "",
            "max": round(float(s.max()), 3) if num else "",
            "constant": bool(num and s.nunique(dropna=True) <= 1),
            "pm_relevance_note": rel,
        })
    m = pd.DataFrame(rows)
    m.to_csv(os.path.join(AD, "sensor_mapping.csv"), index=False)

    documented = (m.documented_description != "Not documented.").sum()
    undocumented = sorted(m[m.documented_description == "Not documented."].column)
    unused_doc = sorted(set(D.index) - set(m.base_signal))

    L = []
    A = L.append
    A("# Sensor Mapping Report - Wind Farm A (Phase 2, Task 1)\n")
    A("Generated by `src/make_sensor_mapping.py` from `feature_description.csv` and "
      "`analysis_data/scada_unique.parquet`.\n")
    A("Descriptions and units are copied **verbatim** from `feature_description.csv`. "
      "No sensor meaning has been inferred, guessed or invented. Any column the "
      "documentation does not cover is recorded as **\"Not documented.\"**\n")
    A("## 1. Coverage summary\n")
    A("| Item | Value |")
    A("|---|---|")
    A("| Columns in the analysis base | {} |".format(len(m)))
    A("| Columns mapped to a documented base signal | {} |".format(
        int((m.role == "Physical measurement").sum())))
    A("| Identifier / metadata columns (no sensor meaning needed) | {} |".format(
        int(m.role.str.startswith(("Identifier", "Metadata")).sum())))
    A("| Columns recorded as \"Not documented.\" | {} |".format(len(undocumented)))
    A("| Columns whose *values* are undocumented | 1 (`status_type_id` code meanings) |")
    A("| Base signals documented in feature_description.csv | {} |".format(len(D)))
    A("| Documented base signals absent from the data | {} |".format(
        len(unused_doc) if unused_doc else 0))
    A("")
    A("Undocumented columns: {}\n".format(
        ", ".join("`{}`".format(c) for c in undocumented) if undocumented else "none"))
    if unused_doc:
        A("Documented but absent from the data: {}\n".format(
            ", ".join("`{}`".format(c) for c in unused_doc)))
    A("`feature_description.csv` documents each **base signal** once; the data expands "
      "several of them into `_avg` / `_max` / `_min` / `_std` aggregate columns of the "
      "same 10-minute interval. The `statistic` column below records which aggregate "
      "each data column is.\n")

    A("## 2. Category breakdown\n")
    A("| Category | Columns |")
    A("|---|---|")
    for cat, n in m.category.value_counts().items():
        A("| {} | {} |".format(cat, n))
    A("")

    A("## 3. Full column mapping\n")
    A("`constant` marks zero-variance columns. `pct_missing` is measured on the "
      "{:,} deduplicated observations.\n".format(len(df)))
    A("| # | Column | Statistic | Documented description | Unit | Category | Role | dtype | "
      "Missing | Unique | Min | Max | Constant |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in m.iterrows():
        A("| {} | `{}` | {} | {} | {} | {} | {} | {} | {} ({}%) | {:,} | {} | {} | {} |".format(
            i + 1, r.column, r.statistic, r.documented_description, r.unit, r.category,
            r.role, r.dtype, r.n_missing, r.pct_missing, r.n_unique, r["min"], r["max"],
            "**yes**" if r.constant else "no"))
    A("")

    A("## 4. Notes on specific columns\n")
    A("- `sensor_46` (*Active power - generator connected in star*) and `sensor_49` "
      "(*Reactive power - generator connected in star*) are **constant zero across all "
      "1,196,747 raw observations**. They carry no information. Phase 1 removed them; "
      "this analysis base retains them so the check is reproducible, but they must be "
      "excluded before modelling.")
    A("- `sensor_14_avg` (*Temperature in generator bearing 1, Non-Drive End*) and "
      "`sensor_22_avg` (*Actual phase displacement*) are the only columns with missing "
      "values: 20 each in the raw data. No imputation has been applied in the analysis "
      "base - the gaps are left visible so that Phase 3 can decide how to treat them.")
    A("- `row_id_in_event` is the raw `id` column, renamed. It is a **per-file row "
      "counter that restarts at 0 in every event file**. `event_info.csv` indexes into "
      "it via `event_start_id` / `event_end_id`. It is meaningless once files are "
      "merged and must never be used as a feature.")
    A("- `status_type_id` has **no documented meaning** in the supplied files. See "
      "`reports/status_analysis.md`.")
    A("- Angular signals are flagged `is_angle=True` in the documentation: "
      "{}. These must not be averaged or differenced naively - they wrap at 360 deg.".format(
          ", ".join("`{}`".format(x) for x in doc[doc.is_angle].sensor_name)))
    A("- Counter signals: the documentation flags `is_counter=True` for "
      "{}.".format(", ".join("`{}`".format(x) for x in doc[doc.is_counter].sensor_name)
                   or "no signal"))
    A("")

    with open(os.path.join(REP, "sensor_mapping_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("Wrote {}/sensor_mapping_report.md".format(REP))
    print("  columns: {}  documented: {}  undocumented: {}".format(
        len(m), documented, len(undocumented)))
    print("  undocumented:", undocumented)
    print("  documented-but-absent:", unused_doc)
    print("\ncategory counts:\n", m.category.value_counts().to_string())


if __name__ == "__main__":
    main()
