# status_type_id Analysis - Wind Farm A (Phase 2, Task 2)

Evidence produced by `src/analyze_phase2.py` and `src/analyze_pre_failure.py`.
All figures are measured on `analysis_data/scada_unique.parquet`
(**425,023 deduplicated observations, 5 turbines**), not on the Phase 1 master.

---

## 1. Is the meaning documented?

**No. Not documented.**

Neither `feature_description.csv` nor `event_info.csv` nor any file in this project
defines what the values of `status_type_id` mean. `feature_description.csv` describes
only the 54 sensor base signals; `status_type_id` is not among them.

Therefore **no name is assigned to any status code in this report.** The codes are
referred to only as `status 0`, `status 3` and `status 4`. Everything below is an
empirical description of how the codes behave, not a claim about what they mean.

---

## 2. Distribution

Three codes occur. Codes 1, 2 and 5 are absent.

| Code | Count | % | Turbines | First seen | Last seen |
|---|---|---|---|---|---|
| 0 | 367,728 | 86.52% | 5 of 5 | 2021-12-31 00:00 | 2023-11-20 00:40 |
| 3 | 9,909 | 2.33% | 5 of 5 | 2022-03-03 19:10 | 2023-10-22 10:10 |
| 4 | 47,386 | 11.15% | 5 of 5 | 2022-03-03 14:00 | 2023-10-19 10:10 |

> The Phase 1 report quoted 1,053,736 / 119,322 / 23,689 for codes 0 / 4 / 3. Those
> counts are inflated by the 64.5% duplicate rows in the Phase 1 master. The counts
> above are the deduplicated truth.

### By turbine (% of that turbine's observations)

| Turbine | status 0 | status 3 | status 4 | Observations |
|---|---|---|---|---|
| A0 | 84.31% | 2.70% | 12.99% | 94,578 |
| A10 | 84.37% | 2.62% | 13.01% | 98,632 |
| A11 | 93.62% | 1.12% | 5.27% | 76,484 |
| A13 | 90.66% | 1.80% | 7.54% | 80,048 |
| A21 | 80.51% | 3.29% | 16.21% | 75,281 |

All five turbines show all three codes. A21 spends the most time in status 4 and also
carries the most labelled anomalies (3); A11 spends the least and carries the fewest (1).

See `reports/figures/fig1_status_distribution.png`.

---

## 3. Episode durations (consecutive runs of the same code)

Computed per turbine on the ordered, deduplicated timeline.

| Code | Episodes | Min | Median | Mean | p95 | Max |
|---|---|---|---|---|---|---|
| 0 | 27 | 10 min | 53.4 days | 94.6 days | 278.6 days | 369.0 days |
| 3 | 24 | 24.2 h | **72.0 h** | 68.8 h | 72.0 h | 72.2 h |
| 4 | 24 | 4.7 h | **335.8 h** | 329.1 h | 377.8 h | 475.2 h |

Two structural regularities are unmistakable:

* **status 4 episodes are almost always exactly 14 days.** 79% fall within 330-340 h,
  and the modal length is 2,016 observations = 336.0 h to the minute.
* **status 3 episodes are almost always exactly 72 hours** (3 days), and status 3
  **immediately follows status 4** in every case observed.

These are not the durations of naturally-occurring operational states. A physical fault
does not last exactly 336.0 hours on nineteen separate occasions across five turbines.
The regularity indicates that these codes were **stamped onto fixed-length windows
during dataset construction**, not recorded live by the turbine controller. This matters
for Phase 3 and is revisited in section 5.

---

## 4. Relationship to the labelled events

### 4.1 Inside the labelled event periods

| Event type | mean % status 0 | mean % status 3 | mean % status 4 |
|---|---|---|---|
| **anomaly** (12 events) | 4.66% | 0.30% | **95.04%** |
| **normal** (10 events) | **100.00%** | 0.00% | 0.00% |

The separation is essentially perfect. Ten of the twelve anomaly periods are 99.9-100.0%
status 4; all ten normal periods are 100.0% status 0. The single exception is event 40
(A10, *Generator bearing failure*), which is 55.94% status 0 / 44.03% status 4 - it is
also the longest event at 757 h.

See `reports/figures/fig6_status_leakage.png`.

### 4.2 Does status 4 occur outside labelled events?

Yes, and this is important:

| | Observations | Share of status 4 |
|---|---|---|
| status 4 **inside** a labelled anomaly | 14,655 | 30.93% |
| status 4 **outside any labelled event** | 32,731 | **69.07%** |

At episode level: **24 status-4 episodes exist; only 11 overlap a labelled anomaly.
13 do not.** The unmatched episodes are concentrated in 2022, where no events are
labelled at all (see `reports/figures/fig2_status_event_timeline.png`).

So status 4 is **not** a complete failure log. Roughly two-thirds of status-4 time is
unlabelled. Either those episodes are non-failure states, or they are failures the
benchmark chose not to label. **The available documentation cannot distinguish these
two possibilities.**

### 4.3 When does status 4 begin relative to event_start?

| Pattern | Events |
|---|---|
| status 4 already active **168.0 h (exactly 7 days)** before `event_start` | 8 anomalies (22, 72, 73, 26, 42, 10, 45, 84) |
| status 4 begins **at** `event_start` (0 h lead) | 2 anomalies (68, 0) |
| status 4 begins 64.8 h before `event_start` | 1 anomaly (51) |
| status 0 at `event_start` | 1 anomaly (40) |
| status 0 at `event_start` | all 10 normal events |

The recurring exact 168.0 h figure is the same construction artefact as the 336 h
episode length: `event_start` frequently sits precisely at the midpoint of a 14-day
status-4 block.

---

## 5. Usefulness assessment

| Purpose | Verdict | Reason |
|---|---|---|
| Normal-operation classification | **Usable** | status 0 is a defensible filter for "turbine running normally". It is what this project used to define baselines and pre-event windows. |
| Warning detection | **Not supported** | No code behaves like a graded warning. There is no code that precedes status 4 in a way that would function as an early alert. |
| Fault detection | **Not usable as ground truth** | 69% of status-4 time is unlabelled, so status 4 cannot be read as "a fault occurred". Its meaning is undocumented. |
| **Predictive-maintenance target** | **MUST NOT be used** | See below. |

### Why status_type_id must not become the ML target or a feature

1. **It is a near-perfect proxy for the label.** A trivial rule - *"anomaly if
   status_type_id == 4"* - reproduces 95% of the anomaly-event observations and
   misclassifies 0% of the normal-event observations. A model given this column would
   learn that rule and report near-perfect accuracy that means nothing.

2. **It is not available in advance in the way a target must be.** For 8 of 12
   anomalies, status 4 is already active 7 days before `event_start`. A model using it
   is not predicting a future failure; it is reading a flag that already encodes the
   answer.

3. **Its meaning is undocumented.** Renaming code 4 to "failure" or code 3 to
   "maintenance" would be an invention. The empirical association with events is
   suggestive, but 69% of status-4 time is unlabelled, which is inconsistent with a
   simple "4 = failure" reading.

4. **The exact 336 h / 72 h / 168 h regularities show the codes were applied to
   constructed windows.** Any model trained on them would be learning the dataset's
   construction, not turbine physics.

**Decision carried into Phase 3:** `status_type_id` may be used *only* as a filter to
select normal-operation observations for training a normal-behaviour model, and as a
descriptive variable in reports. It must be excluded from the feature matrix and must
not define the target.

---

## 6. Reproduction

```
python src/build_analysis_base.py     # corrected base (5 turbines, deduplicated)
python src/analyze_phase2.py          # status, train_test, event statistics
python src/analyze_pre_failure.py     # status onset relative to event_start
```

Outputs: `analysis_data/phase2_stats.json`, `status_by_turbine.csv`,
`status_within_events.csv`, `status_onset.csv`.
