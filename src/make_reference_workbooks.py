"""
Tasks 5 & 6 - Human-readable reference workbooks for Wind Farm A.

  reports/sensor_catalog.xlsx        every column: meaning, unit, category, PM relevance
  reports/wind_farm_A_overview.xlsx  Overview / Turbine_Summary / Sensor_Catalog /
                                     Status_Summary / Event_Summary / Time_Coverage
                                     + Derivable_Later + Leakage_Rules + Data_Files

All sensor meanings come VERBATIM from feature_description.csv. Anything the
documentation does not cover is written as "Not documented." Nothing is invented.

Reads : analysis_data/*, feature_description.csv, event_info.csv
Writes: reports/sensor_catalog.xlsx, reports/wind_farm_A_overview.xlsx
"""

import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from excel_utils import new_workbook, write_kv_sheet, write_table_sheet, finalize  # noqa: E402

AD, REP = "analysis_data", "reports"
STEP = pd.Timedelta(minutes=10)

CATEGORY_RULES = [
    (r"temperature|temp\b", "Temperature"),
    (r"rpm", "Speed (rotational)"),
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

# Which turbine component each documented signal observes. Derived ONLY from the
# documented description text - no meaning is invented.
COMPONENT_RULES = [
    (r"gearbox", "Gearbox"),
    (r"generator bearing", "Generator bearing"),
    (r"stator|inside generator|generator rpm", "Generator"),
    (r"hydraulic", "Hydraulic group"),
    (r"transformer", "HV transformer"),
    (r"igbt|inverter", "Converter"),
    (r"split ring", "Slip ring / brush gear"),
    (r"busbar|grid|phase|voltage|current|frequency", "Grid / electrical"),
    (r"pitch", "Pitch system"),
    (r"rotor|nose cone", "Rotor / hub"),
    (r"nacelle", "Nacelle"),
    (r"hub controller|nacelle controller|vcs|vcp|choke", "Control cabinet"),
    (r"ambient|wind", "Environment"),
]

META = {
    "time_stamp": ("Timestamp of the 10-minute aggregation interval", "datetime",
                   "Timestamp", "Time index",
                   "Ordering and time-based splitting ONLY. Never a model feature."),
    "time_stamp_aligned": ("Timestamp moved onto the common Wind Farm A timeline",
                           "datetime", "Timestamp", "Time index",
                           "Use this when merging event files. Events 40 and 71 carry "
                           "a +1 day native offset."),
    "time_offset_days": ("Timestamp correction applied to this event file", "days",
                         "Metadata", "Provenance",
                         "0 for 20 files; 1.0 for events 40 and 71."),
    "asset_id": ("Turbine identifier as supplied in the raw files", "int",
                 "Identifier", "Turbine",
                 "Grouping key. Values: 0, 10, 11, 13, 21."),
    "turbine_uid": ("Turbine identifier used in this project", "string",
                    "Identifier", "Turbine",
                    "Grouping key for per-turbine models and splits. Never a feature."),
    "event_id": ("Source event-window file (filename == event_id)", "int",
                 "Metadata", "Provenance",
                 "Event-level evaluation and provenance. NEVER a model feature."),
    "row_id_in_event": ("Per-file row counter; event_info indexes into it", "int",
                        "Metadata", "Provenance",
                        "LEAKAGE RISK: restarts at 0 in every file and encodes "
                        "position inside an event window. Never a feature."),
    "train_test": ("Benchmark split flag of the source event window", "string",
                   "Train/prediction metadata", "Metadata",
                   "LEAKAGE RISK: belongs to an event window, not an observation. "
                   "38,406 timestamps carry both values."),
    "status_type_id": ("Operating-status code", "int", "Status information", "Turbine state",
                       "LEAKAGE RISK: code meanings NOT DOCUMENTED, and it is a "
                       "near-perfect proxy for the event label. Permitted ONLY as a "
                       "filter to select normal-operation rows for training."),
}


def base_and_stat(col):
    m = re.match(r"^(.*?)_(avg|max|min|std)$", col)
    return (m.group(1), {"avg": "average", "max": "maximum",
                         "min": "minimum", "std": "std_dev"}[m.group(2)]) if m else (col, "value")


def first_match(rules, text, default):
    low = text.lower()
    for pat, val in rules:
        if re.search(pat, low):
            return val
    return default


def pm_relevance(desc, comp):
    """What Phase 3 could plausibly derive. Physical reasoning, not a validated claim."""
    low = desc.lower()
    if "hydraulic" in low:
        return ("HIGH - the only direct observation of the hydraulic group, which is "
                "the failure mode in 6 of 12 documented anomalies.")
    if "generator bearing" in low:
        return ("HIGH - directly targets the 2 Generator bearing failures. The "
                "drive-end minus non-drive-end difference is self-normalising.")
    if "gearbox" in low:
        return ("HIGH - directly targets the 3 gearbox-related anomalies "
                "(2 Gearbox failure + 1 Gearbox bearings damaged).")
    if "transformer" in low:
        return "MEDIUM - directly targets the 1 Transformer failure. Phase spread is the meaningful quantity."
    if "stator" in low:
        return "MEDIUM - generator electrical condition; phase-to-phase divergence indicates a fault."
    if "rpm" in low:
        return ("MEDIUM - required to interpret every temperature. generator_rpm / rotor_rpm "
                "gives a gearbox-ratio integrity indicator (~113:1, std 0.42-0.45).")
    if re.search(r"grid power|possible grid active", low):
        return ("MEDIUM - the load variable. Mandatory conditioning input, and supports "
                "power-curve deviation. NOTE: values are normalised to 0-1, not kW.")
    if "ambient" in low:
        return ("MANDATORY CONDITIONING - every temperature must be referenced to ambient. "
                "On its own it is seasonal, NOT a fault signal.")
    if "wind" in low and "speed" in low:
        return "MANDATORY CONDITIONING - primary driver of load; used for power-curve deviation."
    if "pitch" in low:
        return "MEDIUM - the hydraulic group actuates pitch, so erratic pitch may reflect hydraulic wear."
    if "nacelle" in low or "nose cone" in low:
        return "LOW/REFERENCE - internal reference temperature; nose cone tracks ambient closely."
    if "direction" in low:
        return "LOW - angular signal. Yaw misalignment affects load. Must not be averaged naively (wraps at 360 deg)."
    if comp == "Converter":
        return "MEDIUM - converter thermal condition."
    if comp == "Grid / electrical":
        return "MEDIUM - phase imbalance in current/voltage indicates winding or connection faults."
    return "LOW - documented, but no direct link to a failure mode present in this dataset."


def build_catalog():
    # feature_description.csv is valid UTF-8, but the degree sign was already lost
    # upstream: the file literally contains U+FFFD (29 of them). Map it to "deg".
    doc = pd.read_csv("feature_description.csv", sep=";", encoding="utf-8")
    doc["unit"] = (doc.unit.fillna("").astype(str)
                   .str.replace("�", "deg", regex=False)
                   .str.replace("°", "deg", regex=False))
    D = doc.set_index("sensor_name")

    ev = pd.read_parquet(os.path.join(AD, "scada_by_event.parquet"))
    uniq_cols = set(pd.read_parquet(os.path.join(AD, "scada_unique.parquet"),
                                    columns=None).columns) if False else None
    rows = []
    for c in ev.columns:
        s = ev[c]
        base, stat = base_and_stat(c)
        if c in META:
            desc, unit, cat, comp, rel = META[c]
            phys, ident, src = "NO", "YES", "Derived in this project" \
                if c in ("turbine_uid", "time_stamp_aligned", "time_offset_days") else "Raw dataset field"
            note = ""
        elif base in D.index:
            desc = str(D.loc[base, "description"])
            unit = str(D.loc[base, "unit"]) or "(none given)"
            cat = first_match(CATEGORY_RULES, desc, "Other (documented)")
            comp = first_match(COMPONENT_RULES, desc, "Not documented.")
            rel = pm_relevance(desc, comp)
            phys, ident, src = "YES", "NO", "feature_description.csv"
            note = []
            if bool(D.loc[base, "is_angle"]):
                note.append("ANGULAR - wraps at 360 deg; do not average or difference naively.")
            if bool(D.loc[base, "is_counter"]):
                note.append("COUNTER signal.")
            if s.notna().any() and s.dropna().eq(0).all():
                note.append("CONSTANT ZERO across all 1,196,747 observations - no information. EXCLUDE.")
            if base in ("power_29", "power_30", "reactive_power_27", "reactive_power_28"):
                note.append("Values are NORMALISED to ~0-1 despite the documented unit.")
            if base == "sensor_31":
                note.append("SCALE INCONSISTENCY: _avg is normalised (-0.29..0.49) while "
                            "_max/_min/_std are raw kVAr (-1002..1003). In 79.4% of rows "
                            "_avg > _max, which is impossible in shared units.")
            note = " ".join(note)
        else:
            desc = unit = cat = comp = rel = "Not documented."
            phys, ident, src, note = "NO", "NO", "Not documented.", ""

        n_missing = int(s.isna().sum())
        rows.append({
            "Column Name": c,
            "Description": desc,
            "Unit": unit,
            "Data Type": str(s.dtype),
            "Category": cat,
            "Physical Sensor?": phys,
            "Identifier/Metadata?": ident,
            "Turbine Component": comp,
            "Statistic": stat,
            "Predictive Maintenance Relevance": rel,
            "Documentation Source": src,
            "Missing Values": n_missing,
            "Min": round(float(s.min()), 4) if pd.api.types.is_numeric_dtype(s) else "",
            "Max": round(float(s.max()), 4) if pd.api.types.is_numeric_dtype(s) else "",
            "Notes": note,
        })
    return pd.DataFrame(rows)


def main():
    os.makedirs(REP, exist_ok=True)
    facts = json.load(open(os.path.join(AD, "verified_facts.json")))
    uniq = pd.read_parquet(os.path.join(AD, "scada_unique.parquet"))
    ev_lvl = pd.read_parquet(os.path.join(AD, "scada_by_event.parquet"),
                             columns=["event_id", "turbine_uid", "train_test",
                                      "status_type_id", "time_stamp_aligned"])
    events = pd.read_csv(os.path.join(AD, "event_index.csv"), sep=";",
                         parse_dates=["event_start", "event_end",
                                      "event_start_aligned", "event_end_aligned"])
    cat = build_catalog()
    phys = cat[cat["Physical Sensor?"] == "YES"]

    # ---------------------------------------------------- TASK 5: sensor catalog
    wb = new_workbook()
    write_table_sheet(wb, cat, "Sensor_Catalog")
    write_kv_sheet(wb, [
        ("-- HOW TO READ THIS FILE --", ""),
        ("Purpose", "Every column of the Wind Farm A dataset, with its documented "
                    "meaning, unit, component and predictive-maintenance relevance."),
        ("Rule", "Descriptions and units are copied VERBATIM from "
                 "feature_description.csv. Nothing is invented. Anything the "
                 "documentation does not cover reads 'Not documented.'"),
        ("Total columns catalogued", int(len(cat))),
        ("Physical sensor columns", int(len(phys))),
        ("Identifier / metadata / status columns", int(len(cat) - len(phys))),
        ("Documented base signals", facts["n_doc_base_signals"]),
        ("-- WHY THERE ARE MORE COLUMNS THAN SIGNALS --", ""),
        ("Explanation", "feature_description.csv documents each BASE SIGNAL once. "
                        "The data expands several of them into _avg / _max / _min / "
                        "_std aggregates of the same 10-minute interval. The "
                        "'Statistic' column records which aggregate each one is."),
        ("-- CATEGORIES --", ""),
    ] + [(k, int(v)) for k, v in phys["Category"].value_counts().items()] + [
        ("-- SENSOR TYPES THAT DO NOT EXIST --", ""),
        ("Vibration / acceleration / acoustic", "ABSENT. No such channel exists. "
         "Bearing and gearbox faults must be inferred thermally."),
        ("Pressure (incl. oil pressure)", "ABSENT. Only oil TEMPERATURE exists."),
        ("Note on sensor_22", "'Actual phase displacement' is an ELECTRICAL "
                              "power-factor quantity, NOT mechanical vibration."),
    ], "How_To_Read", col_widths=(46, 86))
    finalize(wb, os.path.join(REP, "sensor_catalog.xlsx"))
    print("Wrote {}/sensor_catalog.xlsx  ({} columns catalogued)".format(REP, len(cat)))

    # -------------------------------------------------- TASK 6: overview workbook
    span = uniq.time_stamp.max() - uniq.time_stamp.min()
    turbine_years = len(uniq) * 10 / 60 / 24 / 365.25
    wb = new_workbook()

    overview = [
        ("-- WIND FARM A - AT A GLANCE --", ""),
        ("Wind farm", "A (Wind Farm B and C are NOT part of this project)"),
        ("Number of turbines", facts["n_turbines"]),
        ("Turbine asset IDs", ", ".join(str(a) for a in facts["asset_ids"])),
        ("Number of observations (deduplicated)", "{:,}".format(len(uniq))),
        ("Number of columns", int(uniq.shape[1])),
        ("Number of physical sensor columns", int(len(phys))),
        ("Documented base signals", facts["n_doc_base_signals"]),
        ("Date range", "{} to {}".format(uniq.time_stamp.min(), uniq.time_stamp.max())),
        ("Total span", "{} days ({:.2f} years)".format(span.days, span.days / 365.25)),
        ("Sampling interval", "10 minutes"),
        ("Approx. turbine-years of data", "{:.1f}".format(turbine_years)),
        ("Number of event windows / source files", facts["n_events"]),
        ("Anomaly (failure) events", facts["n_anomaly"]),
        ("Normal (control) events", facts["n_normal"]),
        ("-- AUTHORITATIVE DATA --", ""),
        ("Use for Phase 3", "analysis_data/scada_unique.parquet ({:,} rows) and "
                            "analysis_data/scada_by_event.parquet ({:,} rows)".format(
                                len(uniq), facts["rows_by_event"])),
        ("Do NOT use", "cleaned_data/cleaned_scada_data.parquet - it contains "
                       "{:,} duplicate (asset_id, timestamp) rows ({:.2f}%)".format(
                           facts["phase1_duplicates"],
                           facts["phase1_duplicates"] / facts["rows_phase1_master"] * 100)),
        ("Excel copies", "cleaned_data/excel/ - INSPECTION ONLY, never the pipeline input"),
        ("-- DATA QUALITY --", ""),
        ("Duplicate (turbine, timestamp) rows", 0),
        ("Columns with missing values", "{} ({})".format(
            len(facts["missing_unique"]),
            ", ".join("{}={}".format(k, v) for k, v in facts["missing_unique"].items()))),
        ("Constant zero-valued columns", "sensor_46, sensor_49 - exclude from modelling"),
        ("-- SENSOR TYPES ABSENT FROM THIS DATASET --", ""),
        ("Vibration / acceleration / acoustic", "ABSENT"),
        ("Pressure (including oil pressure)", "ABSENT - only oil temperature exists"),
        ("Maintenance / work-order records", "ABSENT"),
        ("Turbine metadata (model, capacity, commissioning)", "ABSENT - anonymised"),
    ]
    write_kv_sheet(wb, overview, "Overview", col_widths=(48, 84))

    # Turbine_Summary
    trows = []
    for uid, s in sorted(facts["turbines"].items()):
        evs = events[events.turbine_uid == uid]
        trows.append({
            "turbine_uid": uid, "asset_id": s["asset_id"],
            "observations": s["rows"], "pct_of_total": s["pct_of_total"],
            "first_timestamp": pd.Timestamp(s["t_min"]), "last_timestamp": pd.Timestamp(s["t_max"]),
            "span_days": (pd.Timestamp(s["t_max"]) - pd.Timestamp(s["t_min"])).days,
            "sampling_interval_min": s["modal_step_min"],
            "pct_intervals_exactly_10min": s["pct_exactly_10min"],
            "gaps_over_10min": s["n_gaps"], "largest_gap_hours": s["largest_gap_h"],
            "event_windows": len(evs),
            "anomaly_events": int((evs.event_label == "anomaly").sum()),
            "normal_events": int((evs.event_label == "normal").sum()),
            "event_ids": ", ".join(str(e) for e in sorted(evs.event_id.tolist())),
            "failure_modes": "; ".join(evs[evs.event_label == "anomaly"]
                                       .event_description.dropna().tolist()) or "none",
        })
    write_table_sheet(wb, pd.DataFrame(trows), "Turbine_Summary")

    write_table_sheet(wb, cat, "Sensor_Catalog")

    # Status_Summary
    st = uniq.status_type_id.value_counts().sort_index()
    ct = pd.crosstab(uniq.turbine_uid, uniq.status_type_id)
    srows = [
        ("-- WHAT IS status_type_id? --", ""),
        ("Documented meaning", "NOT DOCUMENTED. No supplied file defines the codes. "
                               "No name is assigned to any code anywhere in this project."),
        ("Codes present", ", ".join(str(int(k)) for k in st.index)),
        ("-- DISTRIBUTION (deduplicated base) --", ""),
    ]
    for k, v in st.items():
        srows.append(("status_type_id == {}".format(int(k)),
                      "{:,}  ({:.2f}%)".format(int(v), v / len(uniq) * 100)))
    srows += [("-- BY TURBINE (% of that turbine) --", "")]
    for uid in ct.index:
        srows.append((uid, "  ".join("code {}: {:.2f}%".format(c, ct.loc[uid, c] / ct.loc[uid].sum() * 100)
                                     for c in ct.columns)))
    srows += [
        ("-- EMPIRICAL BEHAVIOUR (measured, not documented) --", ""),
        ("status 4 episode length", "median 335.8 h; 19 of 24 episodes fall in 330-340 h "
                                    "(i.e. almost exactly 14 days)"),
        ("status 3 episode length", "median 72.0 h, and always immediately follows status 4"),
        ("Interpretation", "Such exact, repeated durations indicate the codes were stamped "
                           "onto FIXED-LENGTH CONSTRUCTED WINDOWS, not recorded live."),
        ("-- RELATIONSHIP TO THE EVENT LABEL --", ""),
        ("Inside anomaly events", "95.04% status 4, 4.66% status 0"),
        ("Inside normal events", "100.00% status 0"),
        ("status 4 outside any labelled event", "69.07% of all status-4 observations"),
        ("status-4 episodes overlapping an anomaly", "11 of 24"),
        ("-- WHY IT CANNOT BE THE ML TARGET --", ""),
        ("Reason 1", "The rule 'anomaly if status_type_id == 4' alone reproduces 95% of "
                     "anomaly-event observations and 0% of normal-event observations. A "
                     "model given it would report meaningless near-perfect accuracy."),
        ("Reason 2", "For 8 of 12 anomalies it is already active 7 days BEFORE "
                     "event_start - it encodes the answer rather than predicting it."),
        ("Reason 3", "Its meaning is undocumented, and 69% of status-4 time is "
                     "unlabelled, which contradicts a simple '4 = failure' reading."),
        ("PERMITTED USE", "As a FILTER ONLY - select status_type_id == 0 rows to train a "
                          "normal-behaviour model. Never as a feature. Never as the target."),
    ]
    write_kv_sheet(wb, srows, "Status_Summary", col_widths=(46, 90))

    # Event_Summary
    ecols = ["event_id", "turbine_uid", "asset", "event_label", "event_description",
             "event_start_aligned", "event_end_aligned", "event_duration_h",
             "event_start", "event_end", "time_offset_days",
             "event_start_id", "event_end_id", "window_start", "window_end",
             "pred_start", "pred_end"]
    e = events[[c for c in ecols if c in events.columns]].copy()
    e = e.sort_values(["turbine_uid", "event_start_aligned"])
    e["source_file"] = "datasets/" + e.event_id.astype(str) + ".csv"
    e["excel_copy"] = "cleaned_data/excel/event_" + e.event_id.astype(str) + ".xlsx"
    write_table_sheet(wb, e, "Event_Summary")

    # Time_Coverage
    cov = (ev_lvl.assign(month=ev_lvl.time_stamp_aligned.dt.to_period("M").astype(str))
                 .drop_duplicates(subset=["turbine_uid", "time_stamp_aligned"])
                 .groupby(["month", "turbine_uid"]).size().unstack(fill_value=0))
    cov["TOTAL"] = cov.sum(axis=1)
    cov = cov.reset_index()
    write_table_sheet(wb, cov, "Time_Coverage")

    # Derivable_Later  (description only - nothing is computed here)
    write_kv_sheet(wb, [
        ("-- WHAT PHASE 3 CAN DERIVE (NOT COMPUTED YET) --", ""),
        ("Rolling statistics", "Rolling mean / std / min / max over 6 h, 24 h and 7 d windows."),
        ("Rate of change", "First difference and slope of temperatures over time."),
        ("Variability", "Within-interval spread is already supplied as _std columns."),
        ("Temperature rise over ambient", "sensor - sensor_0_avg. Removes seasonal effect."),
        ("Component temperature differences",
         "Generator bearing DE minus NDE; gearbox bearing minus gearbox oil. "
         "Self-normalising - they cancel ambient and load."),
        ("Phase spread", "max minus min across the three stator phases (15/16/17) and "
                         "the three transformer phases (38/39/40). Imbalance indicates a fault."),
        ("Gearbox ratio integrity", "generator_rpm / rotor_rpm. Verified as a tight "
                                    "mechanical constant near 113:1 in normal operation."),
        ("Power-curve deviation", "Actual power minus expected power at the same wind speed."),
        ("Operating-condition normalisation", "Residual of a sensor against its expected "
                                              "value at the same power / speed / ambient bin."),
        ("Normal-behaviour-model residuals", "The central Phase 3 health signal."),
        ("-- WHAT CANNOT BE DERIVED FROM THIS DATA --", ""),
        ("Vibration features", "No vibration channel exists."),
        ("Pressure features", "No pressure channel exists."),
        ("Remaining useful life", "No run-to-failure or degradation-stage labelling."),
        ("Guaranteed failure lead time", "10 of 12 anomalies have no normal-operation data "
                                         "before event_start; labelled horizon is 0-72 h."),
        ("Maintenance due date / repair action", "No maintenance or work-order records exist."),
    ], "Derivable_Later", col_widths=(46, 90))

    # Leakage_Rules
    write_kv_sheet(wb, [
        ("-- MUST NEVER ENTER THE ML FEATURE MATRIX --", ""),
        ("status_type_id", "Near-perfect label proxy. Filter only."),
        ("train_test", "Per-event-window metadata; 38,406 timestamps carry both values."),
        ("row_id_in_event (raw 'id')", "Per-file counter encoding position in the window."),
        ("event_id", "Provenance key - identifies the event directly."),
        ("asset_id / turbine_uid", "Grouping keys. A model could memorise which turbine "
                                   "has more anomalies. Use for splitting only."),
        ("time_stamp / calendar features", "All 22 events fall in 2023 and anomalies cluster "
                                           "seasonally; the model would learn WHEN labelled "
                                           "events happen. Ordering and splitting only."),
        ("sensor_46, sensor_49", "Constant zero - no information."),
        ("Raw un-normalised temperatures", "The strongest apparent 'precursor' in this data is "
                                           "ambient temperature. Condition on operating point first."),
        ("Any row at or after event_start of the scored window", "Direct future leakage."),
        ("Global scalers / PCA fitted on all data", "Fit on the training partition of each fold only."),
        ("-- SCALE TRAP (not leakage, but will corrupt features) --", ""),
        ("sensor_31_avg vs _max/_min/_std", "_avg is normalised (-0.29..0.49); _max/_min/_std "
                                            "are raw kVAr (-1002..1003). _avg > _max in 79.4% "
                                            "of rows. Do not mix them in one feature group."),
        ("power_29 / power_30 / reactive_power_27 / reactive_power_28",
         "Normalised to ~0-1 despite documented kW/kVAr units. There is no physical kW scale."),
    ], "Leakage_Rules", col_widths=(52, 88))

    # Data_Files
    fr = []
    for _, r in events.sort_values("event_id").iterrows():
        fr.append({
            "event_id": int(r.event_id),
            "raw_file": "datasets/{}.csv".format(int(r.event_id)),
            "represents": "EVENT WINDOW (filename == event_id, NOT a turbine id)",
            "turbine_uid": r.turbine_uid, "asset_id": int(r.asset),
            "event_label": r.event_label,
            "event_description": r.event_description if isinstance(r.event_description, str) else "",
            "timestamp_offset_days": float(r.time_offset_days),
            "excel_inspection_copy": "cleaned_data/excel/event_{}.xlsx".format(int(r.event_id)),
        })
    write_table_sheet(wb, pd.DataFrame(fr), "Data_Files")

    finalize(wb, os.path.join(REP, "wind_farm_A_overview.xlsx"))
    print("Wrote {}/wind_farm_A_overview.xlsx".format(REP))
    cat.to_csv(os.path.join(AD, "sensor_catalog.csv"), index=False)
    print("  physical sensor columns: {} | metadata/status: {}".format(
        len(phys), len(cat) - len(phys)))
    print("  categories:\n" + phys["Category"].value_counts().to_string())


if __name__ == "__main__":
    main()
