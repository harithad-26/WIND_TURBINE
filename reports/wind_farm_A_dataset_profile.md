# Wind Farm A - Dataset Profile

**Project:** AI-Based Predictive Maintenance of Wind Turbines Using Machine Learning
**Scope:** Wind Farm A only. Wind Farm B and C are not part of this work.
**Status:** Phase 1 (cleaning) and Phase 2 (understanding) complete. Phase 3 not started.

Every number in this document was measured from the files on disk by
`src/verify_wind_farm_a.py`. Nothing is assumed and no sensor meaning is invented.

**Companion Excel files (easier to browse than this document):**

| File | What it gives you |
|---|---|
| `reports/wind_farm_A_overview.xlsx` | The whole dataset in 9 sheets - start here |
| `reports/sensor_catalog.xlsx` | Every column: meaning, unit, component, PM relevance |
| `cleaned_data/excel/event_<id>.xlsx` | One workbook per event window (22 files) |
| `cleaned_data/excel/by_turbine/asset_<id>.xlsx` | One workbook per turbine (5 files) |

---

# 1. What is Wind Farm A?

Wind Farm A is a set of **10-minute averaged SCADA records from 5 wind turbines**,
covering roughly two years, supplied together with a **documented log of 22 real
operating events** - 12 of them actual component failures.

The dataset arrives as **22 CSV files in `datasets/`**, and this is the single most
important structural fact about it:

> **Each CSV is an EVENT WINDOW, not a turbine.**
> The filename is an `event_id`. `datasets/72.csv` is **event 72**, not turbine 72.

Each file holds roughly one year of history for **one** turbine, ending at or shortly
after one documented event. Because the same turbine appears in several files, the
files **overlap heavily in time** - which is why naively concatenating them produced
64.47% duplicate rows in the Phase 1 master.

What makes this dataset genuinely valuable for predictive maintenance:

* **Real, named failures** - gearbox, generator bearing, hydraulic group, transformer.
* **Exact failure timestamps**, verified to align with the SCADA records (22/22).
* **10 confirmed-healthy control windows**, so a detector can be tested for false alarms.

What it does **not** contain: vibration, pressure, maintenance records, or turbine
metadata. Section 9 lists the consequences.

---

# 2. Turbines

Five turbines. `turbine_uid` is the project-internal name; `asset_id` is the raw field.

| turbine_uid | asset_id | Observations | % of total | First timestamp | Last timestamp | Span | Sampling | Gaps >10 min | Largest gap |
|---|---|---|---|---|---|---|---|---|---|
| A0 | 0 | 94,578 | 22.25% | 2021-12-31 00:00 | 2023-10-22 10:20 | 660 d | 10 min (99.97% exact) | 27 | 13.0 h |
| A10 | 10 | 98,632 | 23.21% | 2021-12-31 00:00 | 2023-11-20 00:40 | 688 d | 10 min (99.94% exact) | 55 | 13.0 h |
| A11 | 11 | 76,484 | 18.00% | 2022-04-04 02:30 | 2023-09-21 00:50 | 534 d | 10 min (99.97% exact) | 21 | 13.0 h |
| A13 | 13 | 80,048 | 18.83% | 2022-03-03 14:00 | 2023-09-13 15:30 | 559 d | 10 min (99.97% exact) | 26 | 13.0 h |
| A21 | 21 | 75,281 | 17.71% | 2022-04-30 13:20 | 2023-10-21 08:40 | 539 d | 10 min (99.94% exact) | 44 | **228.8 h** |

Coverage is even - no turbine dominates. A21 has one unusually long gap of about
9.5 days; the other four never exceed 13 hours.

### Event coverage per turbine

| Turbine | Event windows | Anomaly | Normal | Documented failure modes |
|---|---|---|---|---|
| A0 | 0, 24, 26, 71, 73 | 3 | 2 | Hydraulic group ×2, Generator bearing failure |
| A10 | 3, 10, 17, 40, 42 | 3 | 2 | Hydraulic group, Gearbox failure, Generator bearing failure |
| A11 | 25, 68, 69, 92 | 1 | 3 | Transformer failure |
| A13 | 14, 38, 45, 84 | 2 | 2 | Hydraulic group ×2 |
| A21 | 13, 22, 51, 72 | 3 | 1 | Hydraulic group, Gearbox failure, Gearbox bearings damaged |

---

# 3. Dataset Size

| Measure | Value |
|---|---|
| **Unique observations** | **425,023** |
| Total columns (unique base) | 85 |
| Rows in the event-level table | 1,196,747 (rows repeat across overlapping windows) |
| Columns in the event-level table | 90 |
| Turbines | 5 |
| Time span | 2021-12-31 00:00 -> 2023-11-20 00:40 (689 days, 1.89 years) |
| Sampling interval | 10 minutes |
| Approx. turbine-years of data | **8.1** |
| Source files | 22 event-window CSVs |
| Physical sensor columns | 81 (from 54 documented base signals) |
| Identifier / metadata / status columns | 9 |
| Missing values | 7 in `sensor_14_avg`, 7 in `sensor_22_avg` (0.002%) |
| Duplicate (turbine, timestamp) rows | **0** |

### Storage formats and which file is authoritative

| Path | Format | Rows | Role |
|---|---|---|---|
| `datasets/*.csv` | CSV (`;`) | 22 files | **Raw. Read-only. Never modified.** |
| `cleaned_data/cleaned_scada_data.parquet` | Parquet | 1,196,747 | Phase 1 master. **Contains 771,542 duplicate (asset_id, timestamp) rows - 64.47%.** Superseded. Left untouched. |
| `analysis_data/scada_unique.parquet` | Parquet | **425,023** | **AUTHORITATIVE for modelling.** One row per turbine per timestamp. |
| `analysis_data/scada_by_event.parquet` | Parquet | 1,196,747 | **AUTHORITATIVE for event-level work.** Keeps `event_id` provenance. |
| `cleaned_data/excel/**` | XLSX | - | **Human inspection only.** Never a pipeline input. |

> **Why the duplicates were missed in Phase 1:** `src/clean_data.py` called
> `drop_duplicates()` across all columns *including* `id` - a per-file row counter that
> restarts at 0 in every event file. Being unique by construction, it hid every duplicate.

---

# 4. Column Structure

Every column of `analysis_data/scada_by_event.parquet` falls into one of these classes.

| Class | Count | Columns |
|---|---|---|
| **A. Timestamp** | 2 | `time_stamp` (native), `time_stamp_aligned` (common timeline) |
| **B. Turbine / asset identifier** | 2 | `asset_id` (raw), `turbine_uid` (project) |
| **C. Train/prediction metadata** | 1 | `train_test` |
| **D. Status information** | 1 | `status_type_id` |
| **E. Physical SCADA sensor** | **81** | See section 5 |
| **F. Event-related information** | 2 | `event_id`, `row_id_in_event` |
| **G. Other metadata** | 1 | `time_offset_days` |

The deduplicated table `scada_unique.parquet` carries 85 columns: it drops `event_id`,
`row_id_in_event`, `train_test`, `time_offset_days` and the native `time_stamp`, because
those belong to an *event window* rather than to an observation.

**Not documented:** the *meanings of the `status_type_id` code values*. Every other
column maps to a documented base signal or is an identifier created in this project.

---

# 5. Complete Sensor Inventory

**TOTAL NUMBER OF PHYSICAL SENSORS = 54 documented base signals, expanded into 81 data columns.**

`feature_description.csv` documents each base signal **once**. The data expands several
of them into `_avg` / `_max` / `_min` / `_std` aggregates **of the same 10-minute
interval** - so `wind_speed_3_avg`, `_max`, `_min` and `_std` are four statistics of one
anemometer, not four sensors. The table below lists the 54 real sensors.

### Category breakdown (by base signal)

| Category | Sensors |
|---|---|
| Temperature | 25 |
| Electrical - reactive power | 7 |
| Electrical - active power | 6 |
| Electrical - current | 3 |
| Electrical - voltage | 3 |
| Wind / orientation (angular) | 3 |
| Wind speed | 2 |
| Speed (rotational) | 2 |
| Pitch (angular) | 1 |
| Electrical - power factor | 1 |
| Electrical - grid frequency | 1 |

### Sensor types that DO NOT exist in this dataset

| Type | Status |
|---|---|
| **Vibration / acceleration / acoustic** | **ABSENT.** No such channel. Bearing and gearbox faults must be inferred thermally. |
| **Pressure (including oil pressure)** | **ABSENT.** Only oil *temperature* exists. |
| Strain, oil particle count, oil level | ABSENT |

> Do not mistake `sensor_22` *"Actual phase displacement"* for vibration. It is an
> **electrical power-factor** quantity.

### Full inventory

| # | Base signal | Data columns | Documented description | Unit | Category | Component |
|---|---|---|---|---|---|---|
| 1 | `sensor_0` | `sensor_0_avg` | Ambient temperature | degC | Temperature | Environment |
| 2 | `sensor_1` | `sensor_1_avg` | Wind absolute direction | deg | Wind / orientation | Environment |
| 3 | `sensor_2` | `sensor_2_avg` | Wind relative direction | deg | Wind / orientation | Environment |
| 4 | `wind_speed_3` | `wind_speed_3_` avg/max/min/std | Windspeed | m/s | Wind | Environment |
| 5 | `wind_speed_4` | `wind_speed_4_avg` | Estimated windspeed | m/s | Wind | Environment |
| 6 | `sensor_5` | `sensor_5_` avg/max/min/std | Pitch angle | deg | Pitch | Pitch system |
| 7 | `sensor_6` | `sensor_6_avg` | Temperature in the hub controller | degC | Temperature | Control cabinet |
| 8 | `sensor_7` | `sensor_7_avg` | Temperature in the top nacelle controller | degC | Temperature | Nacelle |
| 9 | `sensor_8` | `sensor_8_avg` | Temperature in the choke coils on the VCS-section | degC | Temperature | Control cabinet |
| 10 | `sensor_9` | `sensor_9_avg` | Temperature on the VCP-board | degC | Temperature | Control cabinet |
| 11 | `sensor_10` | `sensor_10_avg` | Temperature in the VCS cooling water | degC | Temperature | Control cabinet |
| 12 | `sensor_11` | `sensor_11_avg` | Temperature in gearbox bearing on high speed shaft | degC | Temperature | Gearbox |
| 13 | `sensor_12` | `sensor_12_avg` | Temperature oil in gearbox | degC | Temperature | Gearbox |
| 14 | `sensor_13` | `sensor_13_avg` | Temperature in generator bearing 2 (Drive End) | degC | Temperature | Generator bearing |
| 15 | `sensor_14` | `sensor_14_avg` | Temperature in generator bearing 1 (Non-Drive End) | degC | Temperature | Generator bearing |
| 16 | `sensor_15` | `sensor_15_avg` | Temperature inside generator in stator windings phase 1 | degC | Temperature | Generator |
| 17 | `sensor_16` | `sensor_16_avg` | Temperature inside generator in stator windings phase 2 | degC | Temperature | Generator |
| 18 | `sensor_17` | `sensor_17_avg` | Temperature inside generator in stator windings phase 3 | degC | Temperature | Generator |
| 19 | `sensor_18` | `sensor_18_` avg/max/min/std | Generator rpm in latest period | rpm | Speed (rotational) | Generator |
| 20 | `sensor_19` | `sensor_19_avg` | Temperature in the split ring chamber | degC | Temperature | Slip ring / brush gear |
| 21 | `sensor_20` | `sensor_20_avg` | Temperature in the busbar section | degC | Temperature | Grid / electrical |
| 22 | `sensor_21` | `sensor_21_avg` | Temperature measured by the IGBT-driver on the grid side inverter | degC | Temperature | Converter |
| 23 | `sensor_22` | `sensor_22_avg` | Actual phase displacement | (none given) | Electrical - power factor | Grid / electrical |
| 24 | `sensor_23` | `sensor_23_avg` | Averaged current in phase 1 | A | Electrical - current | Grid / electrical |
| 25 | `sensor_24` | `sensor_24_avg` | Averaged current in phase 2 | A | Electrical - current | Grid / electrical |
| 26 | `sensor_25` | `sensor_25_avg` | Averaged current in phase 3 | A | Electrical - current | Grid / electrical |
| 27 | `sensor_26` | `sensor_26_avg` | Grid frequency | Hz | Electrical - grid | Grid / electrical |
| 28 | `reactive_power_27` | `reactive_power_27_` avg/max/min/std | Possible grid capacitive reactive power | kVAr | Electrical - reactive power | Grid / electrical |
| 29 | `reactive_power_28` | `reactive_power_28_` avg/max/min/std | Possible grid inductive reactive power | kVAr | Electrical - reactive power | Grid / electrical |
| 30 | `power_29` | `power_29_` avg/max/min/std | Possible grid active power | kW | Electrical - active power | Grid / electrical |
| 31 | `power_30` | `power_30_` avg/max/min/std | Grid power | kW | Electrical - active power | Grid / electrical |
| 32 | `sensor_31` | `sensor_31_` avg/max/min/std | Grid reactive power | kVAr | Electrical - reactive power | Grid / electrical |
| 33 | `sensor_32` | `sensor_32_avg` | Averaged voltage in phase 1 | V | Electrical - voltage | Grid / electrical |
| 34 | `sensor_33` | `sensor_33_avg` | Averaged voltage in phase 2 | V | Electrical - voltage | Grid / electrical |
| 35 | `sensor_34` | `sensor_34_avg` | Averaged voltage in phase 3 | V | Electrical - voltage | Grid / electrical |
| 36 | `sensor_35` | `sensor_35_avg` | Temperature measured by the IGBT-driver on the rotor side inverter phase1 | degC | Temperature | Converter |
| 37 | `sensor_36` | `sensor_36_avg` | Temperature measured by the IGBT-driver on the rotor side inverter phase2 | degC | Temperature | Converter |
| 38 | `sensor_37` | `sensor_37_avg` | Temperature measured by the IGBT-driver on the rotor side inverter phase3 | degC | Temperature | Converter |
| 39 | `sensor_38` | `sensor_38_avg` | Temperature in HV transformer phase L1 | degC | Temperature | HV transformer |
| 40 | `sensor_39` | `sensor_39_avg` | Temperature in HV transformer phase L2 | degC | Temperature | HV transformer |
| 41 | `sensor_40` | `sensor_40_avg` | Temperature in HV transformer phase L3 | degC | Temperature | HV transformer |
| 42 | `sensor_41` | `sensor_41_avg` | Temperature oil in hydraulic group | degC | Temperature | Hydraulic group |
| 43 | `sensor_42` | `sensor_42_avg` | Nacelle direction | deg | Wind / orientation | Nacelle |
| 44 | `sensor_43` | `sensor_43_avg` | Nacelle temperature | degC | Temperature | Nacelle |
| 45 | `sensor_44` | `sensor_44` | Active power - generator disconnected | Wh | Electrical - active power | Not documented. |
| 46 | `sensor_45` | `sensor_45` | Active power - generator connected in delta | Wh | Electrical - active power | Not documented. |
| 47 | `sensor_46` | `sensor_46` | Active power - generator connected in star | Wh | Electrical - active power | Not documented. |
| 48 | `sensor_47` | `sensor_47` | Reactive power - generator disconnected | VArh | Electrical - reactive power | Not documented. |
| 49 | `sensor_48` | `sensor_48` | Reactive power - generator connected in delta | VArh | Electrical - reactive power | Not documented. |
| 50 | `sensor_49` | `sensor_49` | Reactive power - generator connected in star | VArh | Electrical - reactive power | Not documented. |
| 51 | `sensor_50` | `sensor_50` | Total active power | Wh | Electrical - active power | Not documented. |
| 52 | `sensor_51` | `sensor_51` | Total reactive power | VArh | Electrical - reactive power | Not documented. |
| 53 | `sensor_52` | `sensor_52_` avg/max/min/std | Rotor rpm | rpm | Speed (rotational) | Rotor / hub |
| 54 | `sensor_53` | `sensor_53_avg` | Temperature in the nose cone | degC | Temperature | Rotor / hub |

---

# 6. Status Information

## 6.1 `status_type_id`

**Documented meaning: Not documented.** No supplied file defines the code values, so
this project assigns **no name** to any code.

| Code | Observations | % |
|---|---|---|
| 0 | 367,728 | 86.52% |
| 3 | 9,909 | 2.33% |
| 4 | 47,386 | 11.15% |

Codes 1, 2 and 5 do not occur. All three present codes appear on all 5 turbines.

**What was measured empirically:**

* status-4 episodes have a median length of **335.8 h**, and 19 of 24 fall between
  330 and 340 h - i.e. almost exactly **14 days**.
* status-3 episodes have a median length of **72.0 h**, and always follow status 4.
* Inside anomaly events: **95.04% status 4**. Inside normal events: **100% status 0**.
* But **69.07% of all status-4 observations lie outside any labelled event**, and only
  11 of 24 status-4 episodes overlap an anomaly.

Durations that repeat to the exact minute across five turbines indicate these codes were
**stamped onto fixed-length constructed windows**, not recorded live by a controller.

### Why `status_type_id` is NOT automatically the failure label

1. The rule *"anomaly if `status_type_id == 4`"* alone reproduces 95% of anomaly-event
   observations and 0% of normal-event observations. Any model handed this column would
   learn that rule and report near-perfect accuracy that means nothing.
2. For **8 of 12 anomalies it is already active a full 7 days before `event_start`** -
   it encodes the answer rather than predicting it.
3. Its meaning is undocumented, and 69% of status-4 time is unlabelled - inconsistent
   with a simple "4 = failure" reading.

**Permitted use:** as a **filter only** - select `status_type_id == 0` rows to train a
normal-behaviour model. Never as a feature. Never as the target.

## 6.2 `train_test`

**Documented meaning: Not documented.** Empirically it is the benchmark's per-event
evaluation flag.

**It is a property of an event window, not of an observation.** Because the windows
overlap, **38,406 distinct (turbine, timestamp) pairs are labelled `train` in one event
file and `prediction` in another.**

Within a single event window it is perfectly well behaved - verified 22/22 on all four
checks: both categories present; every `prediction` row strictly later than every
`train` row; the prediction block terminates the window; and it fully contains the
labelled event. Typical shape is ~52,300 train rows (~1 year) then 1,100-4,900
prediction rows.

Globally it is **not** chronological: a `prediction` row from event 40 (Jan 2023) is
earlier than a `train` row from event 17 (Nov 2023).

**Is it useful for our temporal validation?** As a *reference protocol*, yes - it shows
how the benchmark intends each event to be scored. As *our* split, no. The event-level
counts (1,146,154 train / 50,593 prediction) sum over overlapping windows and count most
rows several times, so they do not describe any real partition. This is why `train_test`
is deliberately **excluded** from `scada_unique.parquet`.

---

# 7. Event Information

| Property | Value |
|---|---|
| Total events | **22** |
| Anomaly (real failures) | **12** |
| Normal (healthy control windows) | **10** |
| Turbines covered | 5 of 5 |
| Event IDs | 0, 3, 10, 13, 14, 17, 22, 24, 25, 26, 38, 40, 42, 45, 51, 68, 69, 71, 72, 73, 84, 92 |

### Documented failure modes

| Failure mode | Count | Turbines |
|---|---|---|
| Hydraulic group | 6 | A0 ×2, A10, A13 ×2, A21 |
| Gearbox failure | 2 | A10, A21 |
| Generator bearing failure | 2 | A0, A10 |
| Transformer failure | 1 | A11 |
| Gearbox bearings damaged | 1 | A21 |

The 10 `normal` events have an **empty** description and sit 100% in status 0. They are
**control windows** - confirmed healthy periods, provided so a detector can be measured
for false alarms. They are what makes honest evaluation possible.

### How events relate to the SCADA data

The join is: **`event_id` -> CSV filename**, then **`event_start_id` / `event_end_id` ->
that file's own `row_id_in_event` column** (the raw `id`). These are row indices, not
timestamps and not global IDs.

**Verified: 22/22 exact timestamp matches**, for both start and end.

**One correction was required.** Events **40** and **71** carry timestamps shifted
**+1 day** relative to the other files of the same turbine. This was detected
empirically by matching identical sensor fingerprints across files and taking the modal
time delta; the other 20 files show an offset of exactly zero. After subtracting one day
they agree with their siblings on **100.0000%** of overlapping timestamps.

Left uncorrected, A0 and A10 each look like two different machines - the farm appears to
have 7 turbines instead of 5, and event 40 (*Generator bearing failure*) lands on a
turbine that does not exist. `event_index.csv` therefore carries both the native
(`event_start`) and corrected (`event_start_aligned`) times.

### Two facts that constrain Phase 3

* **All 22 events fall in 2023.** 2022 carries no labels at all, yet contains 13
  status-4 episodes. 2022 is therefore **unlabelled**, not *known-healthy*.
* **Events 51 and 72 on A21 overlap.** Event 72 (*Gearbox failure*,
  2023-10-10 -> 2023-10-17) sits entirely inside event 51 (*Gearbox bearings damaged*,
  2023-10-06 -> 2023-10-17). Both concern the A21 gearbox. Whether they are one physical
  failure recorded twice is **Not documented** - the files do not state the relationship.
  This is a decision to settle before Phase 3.

---

# 8. What We Can Derive Later

Listed for planning only. **Nothing here has been computed, and no feature has been
created.** This is Phase 3 work.

| Derived quantity | Built from | Why it is worth trying |
|---|---|---|
| Rolling statistics (mean, std, min, max over 6 h / 24 h / 7 d) | any sensor | Smooths noise, exposes slow drift |
| Rate of change / slope | temperatures | Degradation shows as trend, not level |
| Within-interval variability | the supplied `_std` columns | Already present - instability proxy |
| Temperature rise over ambient | `sensor_X - sensor_0_avg` | Removes the seasonal component |
| Component temperature differences | generator bearing DE − NDE; gearbox bearing − oil | Self-normalising: cancels ambient and load |
| Phase spread | max − min across stator (15/16/17) and transformer (38/39/40) | Imbalance indicates an electrical fault |
| Gearbox ratio integrity | `generator_rpm / rotor_rpm` | A tight mechanical constant in healthy operation |
| Power-curve deviation | actual vs expected power at the same wind speed | Direct efficiency-loss indicator |
| Operating-condition normalisation | residual against expected value at matched power / speed / ambient | The core of a normal-behaviour model |
| Normal-behaviour-model residuals | all of the above | The central Phase 3 health signal |
| Multi-sensor condition indicators | grouped residuals per component | Enables attributing a score to a subsystem |

**Cannot be derived - the inputs do not exist:** vibration features, pressure features,
oil-condition features, remaining useful life, maintenance history features.

---

# 9. What We CANNOT Claim

Each item below was tested against the data and found unsupported.

| Claim | Verdict | Evidence |
|---|---|---|
| **Exact failure time prediction** ("failure in N hours") | **Not supported** | 10 of 12 anomalies have zero normal-operation rows before `event_start` |
| **Guaranteed lead time** (e.g. "48 hours") | **Not supported** | Prediction-window lead is 0-72 h (median 48 h), and 4 of 12 anomalies have *zero* prediction rows before `event_start` |
| **Remaining useful life (RUL)** | **Not supported** | No run-to-failure histories, no degradation-stage labels |
| **Maintenance due date** | **Not supported** | No maintenance schedule exists in any file |
| **Actual repair recommendation** | **Not supported** | No work-order, repair or CMMS data exists |
| **SMS/alert from real maintenance records** | **Not supported** | No technician, contact or dispatch data; needs an external gateway |
| **Vibration-based diagnosis** | **Not supported** | No vibration channel exists |
| **Power output in kW** | **Not supported** | `power_29`/`power_30` are normalised to ~0-1 despite the documented kW unit |
| **Turbine model / capacity / commissioning date** | **Not supported** | Dataset is anonymised |
| **Real-time monitoring** | **Not supported** | Data ends 2023-11-20; there is no live feed |
| Statistically demonstrated pre-failure sensor drift | **Not demonstrated** | No sensor separates anomalies from the 10 controls at 24 h, 72 h or 7 d after multiple-comparison correction |

### One measurement trap to be aware of

`sensor_31_avg` (Grid reactive power) is **normalised** (−0.29 … 0.49) while
`sensor_31_max`, `_min` and `_std` are in **raw kVAr** (−1002 … 1003). In **79.4%** of
rows `_avg > _max`, which is impossible if they shared units. Do not combine them in one
feature group without rescaling.

---

# 10. Phase 3: Input -> Process -> Output

Planned only. **Not implemented.**

```
CURRENT INPUT
   analysis_data/scada_unique.parquet     425,023 observations, 5 turbines
   analysis_data/scada_by_event.parquet   event provenance for evaluation
   analysis_data/event_index.csv          22 events (12 anomaly / 10 control)
        |
        v
PHASE 3 - FEATURE ENGINEERING
   temperature rise over ambient  |  component temperature differences
   phase spread  |  gearbox ratio integrity  |  power-curve deviation
   rolling statistics 6 h / 24 h / 7 d  |  rates of change
        |
        v
NORMAL-BEHAVIOUR MODEL
   trained ONLY on status_type_id == 0 rows, from the same turbine,
   strictly earlier than the window being scored
        |
        v  residuals = the health signal
        |
PHASE 4 - FEATURE SELECTION
        |
        v
PHASE 5 - ML MODELLING
   Decision Tree / Random Forest / XGBoost on RESIDUALS, scored per event
        |
        v
PHASE 6 - EVALUATION
   Leave-One-Event-Out CV, event-level
   Precision / Recall / F1 / ROC-AUC over 12 anomalies + 10 controls
   confidence intervals reported (small n)
        |
        v
PHASE 7 - PREDICTION / RISK OUTPUT
   anomaly score per turbine per window; score bands; component attribution
        |
        v
PHASE 8 - DASHBOARD
   Streamlit on historical replay
```

**Leakage list carried into Phase 3** (never in the feature matrix): `status_type_id`
(filter only), `train_test`, `row_id_in_event`, `event_id`, `asset_id`/`turbine_uid`,
raw calendar features, `sensor_46`/`sensor_49` (constant zero), and any row at or after
`event_start` of the window being scored.

---

## Reproduction

```
python src/verify_wind_farm_a.py          # Task 1 - verify every number above
python src/make_excel_inspection.py       # Tasks 3 & 4 - event and turbine workbooks
python src/make_reference_workbooks.py    # Tasks 5 & 6 - catalog and overview
```

Raw files in `datasets/` and everything in `cleaned_data/*.parquet` are read-only
throughout. All generated output goes to `analysis_data/`, `reports/` and
`cleaned_data/excel/`.
