# Phase 2 - Sensor, Status and Event Understanding
## AI-Based Predictive Maintenance of Wind Turbines - Wind Farm A

Date: 2026-09-07
Scope: Wind Farm A only (Wind Farm B is a separate workstream).

All figures in this report are measured on a **corrected analysis base** rebuilt from
the 22 raw CSVs by `src/build_analysis_base.py`. The raw files and
`cleaned_data/cleaned_scada_data.parquet` were **not modified**. Section "Important
Findings" explains why the rebuild was necessary.

| Detailed report | Task |
|---|---|
| `reports/sensor_mapping_report.md` | 1 - Sensor mapping |
| `reports/status_analysis.md` | 2 - status_type_id |
| `reports/train_test_analysis.md` | 3 - train_test |
| `reports/event_analysis.md` | 4 - Events |
| `reports/pre_failure_observation_analysis.md` | 5 - Pre-failure behaviour |
| `reports/potential_pm_signals.md` | 6 - Candidate PM signals |
| `reports/figures/` | 7 - Six figures |

---

# Sensor Mapping

All **85 columns** of the analysis base were cross-checked against
`feature_description.csv`.

| Item | Value |
|---|---|
| Columns mapped to a documented base signal | **81** |
| Identifier / metadata columns | 3 (`turbine_uid`, `asset_id`, `time_stamp`) |
| Columns recorded as "Not documented." | **0** |
| Documented base signals absent from the data | 0 |
| Columns whose *values* are undocumented | 1 (`status_type_id` code meanings) |

The documentation is complete at the signal level: 54 base signals expand into 81 data
columns via `_avg` / `_max` / `_min` / `_std` aggregates of the same 10-minute interval.
Dominant categories: temperature (25 columns), reactive power (16), active power (12),
rotational speed (8).

Notable: `sensor_46` and `sensor_49` (*Active / Reactive power - generator connected in
star*) are **constant zero across all 1,196,747 observations**. Only `sensor_14_avg` and
`sensor_22_avg` have missing values - 7 each on the deduplicated base. **No vibration,
acceleration or acoustic channel exists.**

---

# Status Type Analysis

**The meaning of `status_type_id` is Not documented.** No file in this project defines
the codes, so none is named in any report.

Three codes occur (deduplicated, 425,023 observations):

| Code | Count | % | Episodes | Median episode |
|---|---|---|---|---|
| 0 | 367,728 | 86.52% | 27 | 53.4 days |
| 3 | 9,909 | 2.33% | 24 | **72.0 h** |
| 4 | 47,386 | 11.15% | 24 | **335.8 h** |

Two structural regularities: status-4 episodes are almost always **exactly 336.0 h**
(14 days - 19 of 24 episodes fall in 330-340 h) and status-3 episodes almost always
**exactly 72.0 h**, always immediately following status 4. Physical faults do not last
exactly 336.0 hours nineteen times. These codes were stamped onto **fixed-length
constructed windows**, not recorded live.

Relationship to the labels is near-perfect - and therefore dangerous:

| Event type | mean % status 0 | mean % status 4 |
|---|---|---|
| anomaly (12) | 4.66% | **95.04%** |
| normal (10) | **100.00%** | 0.00% |

But status 4 is **not** a failure log: **69.07% of status-4 observations lie outside any
labelled event**, and 13 of 24 status-4 episodes overlap no event at all (mostly in 2022,
which carries no labels).

---

# Train/Test Metadata Analysis

**The meaning of `train_test` is Not documented.** Empirically it is the benchmark's
per-event evaluation flag.

**It is a property of an event window, not of an observation.** Because the 22 event
windows overlap in time, **38,406 distinct (turbine, timestamp) pairs are labelled
`train` in one event file and `prediction` in another.**

Within any single event window the design is clean - verified 22/22 on all four checks:
both categories present, every prediction row strictly later than every train row, the
prediction block terminating the window, and fully containing the labelled event.
Globally it is not chronological: a `prediction` row from event 40 (January 2023) is
earlier than a `train` row from event 17 (November 2023).

The Phase 1 figure of 1,146,154 train / 50,593 prediction is a sum over overlapping
windows in which most rows are counted several times. It is not a split of the dataset.

---

# Event Analysis

**Usable failure events exist, and they are the strongest asset in this dataset.**

| Property | Value |
|---|---|
| Events | 22 (**12 anomaly**, **10 normal**) |
| Turbines covered | 5 of 5 |
| Alignable to SCADA observations | **22 / 22 verified exactly** |

The join was verified, not assumed: `event_id` equals the raw CSV filename, and
`event_start_id` / `event_end_id` index that file's own `id` column - **22/22 exact
timestamp matches** for both start and end.

Failure modes: Hydraulic group (6), Gearbox failure (2), Generator bearing failure (2),
Transformer failure (1), Gearbox bearings damaged (1).

The 10 `normal` events have empty descriptions and sit 100% in status 0. They are
**control windows** - confirmed-healthy periods provided so a detector can be tested for
false alarms. They make rigorous evaluation possible and are used as the control group
throughout Phase 2.

Two qualifications: events **51 and 72 on A21 overlap** (event 72 is entirely inside
event 51, both gearbox) and are almost certainly one physical failure recorded twice
(**Not documented**); and **all 22 events fall in 2023**, so 2022 is *unlabelled*, not
*known-healthy*.

---

# Pre-Failure Observation Analysis

**Result: no sensor separates anomalies from the normal control group at any horizon.**

The dominant constraint is data availability, not signal strength:

| Pre-event window | Anomalies with usable status-0 data | Normals |
|---|---|---|
| 1 h - 24 h | **3 of 12** | 10 of 10 |
| 72 h - 168 h | **4 of 12** | 10 of 10 |

For 8 of 12 anomalies the turbine is already in status 4 for a full 7 days before
`event_start`. Independently, **10 of 12 anomalies have zero normal-operation rows in
the prediction window before `event_start`**, and prediction-window lead time is only
**0-72 h (median 48 h)**.

Testing 20 documented sensors with power-binned residuals against the control group
(Mann-Whitney U, Bonferroni alpha = 0.0025):

| Horizon | n anomaly vs normal | p < 0.05 uncorrected | Surviving correction |
|---|---|---|---|
| 24 h | 3 vs 10 | 1 of 20 | **0** |
| 72 h | 4 vs 10 | 0 of 20 | **0** |
| 168 h | 4 vs 10 | 0 of 20 | **0** |

Three observations make the negative result convincing rather than merely inconclusive:

1. The **two largest anomaly signals at 24 h are ambient temperature (+1.15) and nose
   cone temperature (+1.10)**, which tracks ambient. Both are seasonal, not mechanical.
2. **Normal event 13 (A21) deviates more (+1.98) than either Generator bearing
   failure** - a confirmed-healthy window looks more alarming than a real failure.
3. The **two Generator bearing failures disagree in sign** (ambient +2.71 vs -0.94),
   because the signature is seasonal (August vs December), not physical. For neither
   event are the generator bearing temperatures among the top three sensors.

With 3 anomalies vs 10 normals the smallest obtainable two-sided p-value is
2/C(13,3) = 0.00699 - **above** the corrected threshold, so a corrected-significant
result at 24 h is arithmetically impossible whatever the effect size. This analysis
**fails to demonstrate** a precursor and is barely powered to demonstrate one.

---

# Potential Predictive-Maintenance Signals

Every documented failure mode has at least one directly relevant documented sensor.
Ranked by number of events the signal could plausibly explain:

| Rank | Signal(s) | Events | Documented meaning |
|---|---|---|---|
| 1 | `sensor_41_avg` (+ `sensor_5_std`) | 6 | Temperature oil in hydraulic group (+ pitch angle std dev) |
| 2 | `sensor_13_avg`, `sensor_14_avg` | 2 | Generator bearing 2 (DE) / bearing 1 (NDE) temperature |
| 3 | `sensor_11_avg`, `sensor_12_avg` | 3 | Gearbox HSS bearing temp / gearbox oil temp |
| 4 | `sensor_38/39/40_avg` | 1 | HV transformer temperature L1 / L2 / L3 |
| 5 | `sensor_15/16/17_avg` | supporting | Stator winding temperature phases 1-3 |
| 6 | `power_30_avg`, `wind_speed_3_avg`, `sensor_0_avg`, `sensor_52_avg`, `sensor_18_avg` | all | Mandatory conditioning variables |

**Vibration data does not exist** in this dataset. Bearing and gearbox degradation must
be inferred thermally - slower and less specific than vibration-based diagnosis.

These are **physically motivated hypotheses**, justified by documented meaning and by the
failure modes present. None has been empirically validated as a predictor here.

---

# Important Findings

## F1. The Phase 1 master dataset contains 64.5% duplicate rows

Each `datasets/N.csv` is an **event window** whose filename equals an `event_id` - not a
turbine. `src/clean_data.py:64` calls `drop_duplicates()` across all columns including
`id`, a per-file row counter that restarts at 0 in every file. Being unique by
construction, it masked every duplicate.

| | Rows |
|---|---|
| Phase 1 master | 1,196,747 |
| **Genuinely unique (turbine, timestamp)** | **425,023** |
| Duplicated | 771,724 (**64.49%**) |

Multiplicity runs up to 5. Every statistic in the Phase 1 reports that counts
observations is inflated - including the status distribution and the train/test split.

## F2. Two event files carry a +1 day timestamp offset

Events **40** (asset 10) and **71** (asset 0) are shifted **exactly +1 day** relative to
the other files of the same turbine. Detected empirically by fingerprint matching; the
other 20 files show an offset of exactly zero, and after correction the shifted files
agree with their siblings on **100.0000%** of overlapping timestamps.

Uncorrected, this makes A0 and A10 each look like two different machines - **the farm
appears to have 7 turbines instead of 5** - and event 40 (*Generator bearing failure*)
lands on a turbine that does not exist. Phase 1 sorted and interpolated grouped by
`asset_id`, so it interleaved and interpolated across the offset data.

**Corrected: 5 turbines - A0, A10, A11, A13, A21.**

## F3. Event provenance was lost, and it is the key to the whole dataset

The Phase 1 concatenation kept no `event_id`, so `event_info.csv` - the only genuine
ground truth available - could not be joined to any row. The corrected base restores it.

## F4. status_type_id is a near-perfect label proxy and must not be a feature

The rule *"anomaly if status_type_id == 4"* reproduces 95% of anomaly-event observations
and 0% of normal-event observations. For 8 of 12 anomalies it is already active 7 days
before `event_start`. Any model given this column will report near-perfect accuracy that
means nothing.

## F5. The dataset does not support failure-lead-time prediction

10 of 12 anomalies have no normal-operation data before `event_start`; the labelled lead
horizon is 0-72 h; and no sensor separates anomalies from controls at any horizon.

## F6. The effective sample size is 12, not 1.2 million

Evaluation is per **event**. Twelve anomalies across five failure modes - one Transformer
failure, and two gearbox events that are probably one physical failure. Any per-failure-
mode model is unsupportable. Confidence intervals will be wide and must be reported.

## F7. Data quality of the corrected base is good

Sampling is on a strict 10-minute grid: 99.94-99.97% of consecutive intervals are exactly
10 minutes. Gaps are few (21-55 per turbine); the largest is 13.0 h except on A21, which
has one 228.8 h gap. Missing values: 7 each in `sensor_14_avg` and `sensor_22_avg`. Zero
conflicting duplicates and zero status conflicts after alignment.

## F8. Dashboard feasibility - what the data actually supports

| Dashboard item | Supported? | Basis |
|---|---|---|
| Sensor readings | **Yes** | 81 documented sensor columns |
| Time-series trends | **Yes** | Strict 10-min grid, 5 turbines, ~2 years |
| Turbine-wise information | **Yes** | 5 turbines, 425,023 observations |
| Turbine health score | **Yes, as a derived index** | Normal-behaviour-model residual. An engineering indicator, **not** a calibrated failure probability. |
| Active alerts | **Yes** | Threshold crossings of that index; threshold set on the 10 control windows |
| Recent predictions | **Yes** | Scored prediction windows |
| Risk level | **Partial** | Ordinal banding of the anomaly score. Bands must be labelled as score bands, not probabilities. |
| Failure risk (as a probability) | **No** | 12 events cannot calibrate a probability |
| **Estimated lead time before failure** | **No** | F5. Would require fabricating a horizon the data does not contain |
| **Maintenance recommendation** | **No** | No maintenance-action, work-order or repair data exists anywhere in the dataset |
| Model performance | **Yes, with wide intervals** | Event-level over 12 anomalies + 10 controls; report CIs |

Two dashboard items from the original brief - *estimated lead time* and *maintenance
recommendation* - **cannot be produced from this dataset without fabrication.** They
should be dropped, or shown as explicitly non-data-driven placeholders.

---

# Decisions Required Before Feature Engineering

| # | Decision | Recommendation |
|---|---|---|
| D1 | Which base does Phase 3 use? | `analysis_data/scada_unique.parquet` (425,023 rows) for modelling; `scada_by_event.parquet` for event-level evaluation. Not the Phase 1 master. |
| D2 | Are events 51 and 72 one failure or two? | Treat as **one** gearbox failure on A21. Counting them twice inflates the positive count and scores one failure twice. |
| D3 | How is 2022 treated? | As **unlabelled**, not known-healthy. 13 status-4 episodes there overlap no event. Usable for normal-behaviour training only after filtering to status 0. |
| D4 | Is `status_type_id` allowed as a training filter? | **Yes as a filter only** (select status 0 for normal-behaviour training). **Never as a feature or target.** |
| D5 | Per-failure-mode or single model? | **Single** anomaly detector. Per-mode modelling is unsupportable at n = 1-6. |
| D6 | How are the 20 raw missing values handled? | Leave visible; drop or forward-fill those 7 rows at feature-build time. Immaterial at 0.002%. |
| D7 | Do the two dropped dashboard items get removed? | **Requires your decision.** Recommendation: remove *estimated lead time* and *maintenance recommendation*. |
| D8 | Should Phase 1 artefacts be regenerated? | Optional. `cleaned_data/` is superseded by `analysis_data/` for all analysis. Left untouched as instructed. |

---

# READY FOR PHASE 3?

## **YES** - with the prediction target redefined.

Phase 2 is complete: every sensor is documented, the status and split fields are
characterised, the event log is verified to align exactly with the SCADA data, and the
data-integrity defects that would have invalidated Phase 3 have been found and corrected.
No information needed to proceed is missing.

The qualification is that the **originally envisaged target - "predict failure N hours
ahead" - is not supported by this data** (F5). Proceeding with it would mean inventing a
signal that the evidence does not show. The target below is what the data does support.

### 1. What will become the prediction target

**An event-level binary anomaly label, scored by an unsupervised normal-behaviour model.**

* **Target:** `event_info.event_label` - `anomaly` (12) vs `normal` (10) - assigned to
  the **event window**, not to individual observations. After merging events 51 and 72
  (D2): **11 anomaly windows vs 10 control windows**.
* **Model form:** a per-turbine normal-behaviour model trained **only** on
  `status_type_id == 0` observations that are strictly earlier than the window being
  scored. It predicts expected sensor values from operating conditions (power, wind
  speed, rotational speed, ambient temperature); the **residual** is the health signal.
* **Scoring:** aggregate residuals over an event window into one score; an event is
  flagged if the score exceeds a threshold calibrated on the control windows.
* **Metrics:** event-level detection rate over 11 anomalies, false-alarm rate over 10
  controls, with confidence intervals. **No per-observation accuracy** - it would be
  dominated by the class imbalance and by F4.

This is **anomaly detection with event-level evaluation**, not failure-horizon
regression. The distinction must be stated plainly in the final report and dashboard.

### 2. Which event/status information will be used

| Used | How |
|---|---|
| `event_info.csv` - `event_label` | **The ground truth.** The only documented label. |
| `event_info.csv` - `event_start` / `event_end` (aligned) | Define the scored window and the training cut-off. |
| `event_id` | Provenance, grouping and event-level evaluation. Never a feature. |
| `status_type_id == 0` | **Filter only** - selects normal-operation rows for training. |
| `turbine_uid` | Grouping key for per-turbine models and splitting. |

`event_description` is used for reporting per-failure-mode results descriptively only -
**not** as a modelling class (F6).

### 3. What must NOT be used because of leakage

| Excluded | Reason |
|---|---|
| **`status_type_id` as a feature or target** | Near-perfect label proxy: 95% of anomaly-event observations, 0% of normal. Active 7 days before `event_start` for 8 of 12 anomalies. Meaning undocumented. |
| **`train_test`** | Per-event-window metadata; 38,406 timestamps carry both values. |
| **`row_id_in_event`** (raw `id`) | Per-file row counter correlated with position inside an event window. |
| **`event_id`, `asset_id`, `turbine_uid` as features** | Provenance/grouping keys. A model could memorise which turbine has more anomalies. |
| **Any observation at or after `event_start`** of the window being scored, in training | Direct future leakage. |
| **Any data from the scored event window itself**, in training | Including its `train` prefix if that overlaps another window's scored period. |
| **`sensor_46`, `sensor_49`** | Constant zero - no information. |
| **Raw calendar features** (month, day-of-year) | All 22 events fall in 2023 and anomalies cluster seasonally; the model would learn *when* labelled events happen. |
| **Raw un-normalised temperatures as health indicators** | The strongest apparent precursor in the data is ambient temperature. Condition on operating point first. |
| **Global statistics computed over the full dataset** (scaler means, PCA fits) | Must be fitted on the training partition only, per fold. |

### 4. What type of time-based split should be used

**Leave-One-Event-Out cross-validation with a strict per-fold temporal cut-off, grouped
by turbine.**

For each of the 21 event windows in turn (after merging 51/72):

1. **Hold out** that event window as the test set.
2. **Train** the normal-behaviour model only on observations that are
   (a) from the **same turbine**, (b) **strictly earlier** than the held-out window's
   start, and (c) `status_type_id == 0`.
3. **Score** the held-out window and compare to a threshold calibrated on control
   windows from *other* folds only.

Properties that make this the right choice:

* **No random splitting** - every fold respects chronological order.
* **No future leakage** - training data always precedes the scored window.
* **Overlap-safe** - because event windows overlap in time, the cut-off must be applied
  on the *aligned timeline*, not per file. This is why `analysis_data/scada_unique.parquet`
  exists.
* **Maximises the 21 events available** - a single global holdout would leave only 2-3
  anomalies to evaluate on.

Report per-fold results and the aggregate with confidence intervals. With 11 anomalies,
a single additional miss changes the detection rate by ~9 percentage points; the final
report must say so rather than quoting a bare accuracy figure.

---

## Reproduction

```
python src/build_analysis_base.py     # corrected base: 5 turbines, deduplicated, aligned
python src/analyze_phase2.py          # status, train_test, event statistics
python src/analyze_pre_failure.py     # pre-event drift vs the normal control group
python src/make_sensor_mapping.py     # sensor mapping report
python src/explore_data.py            # six figures
```

Raw files and `cleaned_data/` are read-only throughout; all outputs go to
`analysis_data/` and `reports/`.
