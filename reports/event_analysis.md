# Event Analysis - Wind Farm A (Phase 2, Task 4)

Source: `event_info.csv` (22 rows), cross-checked against the 22 raw event CSVs.
Evidence produced by `src/build_analysis_base.py` and `src/analyze_phase2.py`.

---

## 1. Do usable failure events exist?

**Yes.** This is the strongest asset in the dataset.

`event_info.csv` is a genuine, structured event log with named failure modes, exact
start and end timestamps, and an explicit turbine reference. It is documented well
enough to be used as ground truth - unlike `status_type_id`.

| Property | Value |
|---|---|
| Events | 22 |
| **anomaly** events | **12** |
| **normal** (control) events | **10** |
| Turbines covered | 5 of 5 |
| Named failure modes | 5 distinct |
| Events with a parseable start and end timestamp | 22 / 22 |
| Events alignable to SCADA observations | **22 / 22** |

---

## 2. Fields in event_info.csv

| Field | Content | Notes |
|---|---|---|
| `asset` | turbine id | Matches `asset_id` in the SCADA files. |
| `event_id` | event identifier | **Equals the raw CSV filename** - `datasets/68.csv` is event 68. This is the join key that Phase 1 discarded. |
| `event_label` | `anomaly` or `normal` | The ground-truth class. Only these two values occur. |
| `event_start`, `event_end` | timestamps | 10-minute resolution, same grid as the SCADA data. |
| `event_start_id`, `event_end_id` | integers | Row indices into that file's own `id` column, **not** timestamps or global ids. |
| `event_description` | free text | Populated for all 12 anomalies; empty for all 10 normal events. |

---

## 3. Alignment with SCADA observations - verified

Alignment was checked exhaustively, not assumed.

**Check 1 - do `event_start_id` / `event_end_id` index the per-file `id` column?**
For each event, the row whose `id == event_start_id` was located in the corresponding
CSV and its timestamp compared to `event_start`.

> **Result: 22 / 22 exact matches, for both start and end.**

This confirms the intended join: `event_info.event_id` -> CSV filename, then
`event_start_id` -> that file's `id` column.

**Check 2 - a timestamp offset in two files.**
Events **40** and **71** carry timestamps shifted **+1 day** relative to the other event
files of the same turbine. Detected empirically by matching identical sensor
fingerprints across files and taking the modal time delta; all 20 other files show an
offset of exactly zero. After subtracting one day, those two files agree with their
siblings on **100.0000%** of overlapping timestamps.

Left uncorrected this is damaging: turbines A0 and A10 each appear to be two different
machines, and the anomaly in event 40 (*Generator bearing failure*) lands on a
non-existent turbine. `src/build_analysis_base.py` detects and corrects it, and writes
both `event_start`/`event_end` (native) and `event_start_aligned`/`event_end_aligned`
to `analysis_data/event_index.csv`. **All analysis in Phase 2 uses the aligned columns.**

---

## 4. What the events are

All 12 anomalies are **component failures**, not alarms, warnings or scheduled
maintenance. The descriptions name the failing subsystem directly.

| Failure mode | Count | Affected turbines |
|---|---|---|
| Hydraulic group | 6 | A0 (x2), A10, A13 (x2), A21 |
| Gearbox failure | 2 | A10, A21 |
| Generator bearing failure | 2 | A0, A10 |
| Transformer failure | 1 | A11 |
| Gearbox bearings damaged | 1 | A21 |

The 10 `normal` events have an **empty** `event_description` and sit entirely in
status 0. They are not failures - they are **control windows**: periods of confirmed
healthy operation, deliberately provided so that a detector can be tested for false
alarms. This is what makes rigorous evaluation possible, and it is used as the control
group throughout `reports/pre_failure_observation_analysis.md`.

---

## 5. Full event list (aligned timeline)

| event_id | turbine | label | description | start | end | duration (h) | obs |
|---|---|---|---|---|---|---|---|
| 71 | A0 | normal | | 2023-01-01 00:00 | 2023-01-15 00:00 | 336.0 | 2,017 |
| 24 | A0 | normal | | 2023-04-27 15:00 | 2023-05-11 11:20 | 332.3 | 1,995 |
| 73 | A0 | anomaly | Hydraulic group | 2023-06-10 11:40 | 2023-06-17 11:40 | 168.0 | 1,009 |
| 0 | A0 | anomaly | Generator bearing failure | 2023-08-06 06:10 | 2023-08-20 06:10 | 336.0 | 2,012 |
| 26 | A0 | anomaly | Hydraulic group | 2023-10-12 10:20 | 2023-10-19 10:20 | 168.0 | 1,009 |
| 40 | A10 | anomaly | Generator bearing failure | 2022-12-25 00:00 | 2023-01-25 13:00 | 757.0 | 4,508 |
| 3 | A10 | normal | | 2023-04-27 03:00 | 2023-05-18 01:10 | 502.2 | 3,014 |
| 42 | A10 | anomaly | Hydraulic group | 2023-09-09 15:50 | 2023-09-16 15:50 | 168.0 | 1,007 |
| 10 | A10 | anomaly | Gearbox failure | 2023-10-11 08:40 | 2023-10-18 08:40 | 168.0 | 981 |
| 17 | A10 | normal | | 2023-11-02 15:20 | 2023-11-16 00:40 | 321.3 | 1,917 |
| 92 | A11 | normal | | 2023-04-05 02:30 | 2023-04-14 10:00 | 223.5 | 1,342 |
| 25 | A11 | normal | | 2023-05-23 06:50 | 2023-06-05 02:30 | 307.7 | 1,847 |
| 68 | A11 | anomaly | Transformer failure | 2023-07-28 13:20 | 2023-08-11 13:10 | 335.8 | 2,014 |
| 69 | A11 | normal | | 2023-09-04 00:50 | 2023-09-18 00:50 | 336.0 | 2,017 |
| 14 | A13 | normal | | 2023-03-05 14:00 | 2023-03-12 18:40 | 172.7 | 1,037 |
| 45 | A13 | anomaly | Hydraulic group | 2023-04-19 18:10 | 2023-04-26 18:10 | 168.0 | 1,008 |
| 38 | A13 | normal | | 2023-07-01 15:40 | 2023-07-15 07:40 | 328.0 | 1,824 |
| 84 | A13 | anomaly | Hydraulic group | 2023-09-05 15:30 | 2023-09-12 15:30 | 168.0 | 1,005 |
| 13 | A21 | normal | | 2023-05-03 13:20 | 2023-05-24 10:20 | 501.0 | 3,007 |
| 22 | A21 | anomaly | Hydraulic group | 2023-08-12 09:50 | 2023-08-19 10:00 | 168.2 | 1,005 |
| 51 | A21 | anomaly | Gearbox bearings damaged | 2023-10-06 01:30 | 2023-10-17 16:10 | 278.7 | 1,673 |
| 72 | A21 | anomaly | Gearbox failure | 2023-10-10 08:40 | 2023-10-17 08:40 | 168.0 | 1,009 |

Durations: min 168.0 h, median 293.2 h, mean 291.5 h, max 757.0 h.
Note that **seven of the twelve anomalies last exactly 168.0 h** (an eighth lasts
168.2 h) - the same fixed-window construction pattern seen in `status_type_id`.

---

## 6. Findings that constrain Phase 3

### 6.1 All labelled events are in 2023; the status codes are not

Every one of the 22 events falls between 2023-01-01 and 2023-11-16. But status 4
episodes occur throughout 2022 as well - **13 of 24 status-4 episodes overlap no
labelled event.** The 2022 data is therefore *unlabelled*, not *known-healthy*.
Treating 2022 as a clean normal period is an assumption the data does not support.
See `reports/figures/fig2_status_event_timeline.png`.

### 6.2 Two anomalies on A21 overlap each other

| | |
|---|---|
| Event 51 | *Gearbox bearings damaged*, 2023-10-06 01:30 -> 2023-10-17 16:10 |
| Event 72 | *Gearbox failure*, 2023-10-10 08:40 -> 2023-10-17 08:40 |

Event 72 is entirely contained within event 51, and both concern the A21 gearbox. These
are almost certainly **two records of one physical failure** (progressive bearing damage
culminating in gearbox failure), not two independent events. **Not documented** - the
files do not state the relationship.

Phase 3 must not count these as two independent positives; doing so would overstate the
effective sample size and let one failure be scored twice.

### 6.3 The effective sample size is 12, not 1.2 million

The unit of analysis for evaluation is the **event**, not the observation. There are 12
anomalies spread over 5 failure modes and 5 turbines - as few as **one** example of
Transformer failure and (after merging 51/72) **two** of gearbox failure. Per-failure-mode
modelling is not statistically supportable. Only *Hydraulic group*, with 6 events, has
enough instances to be discussed as a class in its own right, and even that is small.

### 6.4 There is very little pre-event data

Measured on the prediction windows (see `reports/train_test_analysis.md` for the table):

* Prediction-window lead before `event_start`: **0-72 h, median 48 h.**
* **4 of 12** anomalies have **zero** prediction rows before `event_start`.
* **10 of 12** anomalies have **zero normal-operation (status 0)** rows before
  `event_start` - the turbine is already in status 4.

This is developed in `reports/pre_failure_observation_analysis.md` and is the single
biggest constraint on what can be built.

---

## 7. Conclusion

Usable failure events **do exist**, they are well documented, and they align exactly
with the SCADA observations (22/22, once the two-file offset is corrected). The event
log is a sound basis for ground truth.

The limitations are sample size (12 anomalies), a very short pre-event horizon, and one
duplicated failure. These bound what Phase 3 can honestly attempt - they do not
invalidate the data.

**No ML target is created in this report.** The target is specified in
`reports/phase2_understanding_report.md`.

---

## 8. Reproduction

```
python src/build_analysis_base.py
python src/analyze_phase2.py
```

Outputs: `analysis_data/event_index.csv`, `analysis_data/timestamp_offsets.csv`,
`analysis_data/status_within_events.csv`.
