# train_test Analysis - Wind Farm A (Phase 2, Task 3)

Evidence produced by `src/analyze_phase2.py`. Measured on
`analysis_data/scada_by_event.parquet` (1,196,747 event-level rows across 22 event files).

---

## 1. Is the meaning documented?

**Not documented.** No file in this project states what `train_test` means.

What follows is therefore an empirical characterisation of how the field behaves. It is
strong enough to support a firm conclusion about how the field must *not* be used.

---

## 2. The decisive structural finding

**`train_test` is a property of an event window, not a property of an observation.**

Each of the 22 raw CSVs is one event window (the filename equals the `event_id`).
Because the windows overlap in time, the same turbine-timestamp appears in up to five
files - and it carries a *different* `train_test` value in different files.

> **38,406 distinct (turbine, timestamp) pairs are labelled `train` in one event file
> and `prediction` in another.**

Concrete example - turbine A0 at 2023-08-04 06:10 through 2023-08-06 06:00:
* in event file `0.csv` these rows are `prediction` (they lead into the Generator
  bearing failure that file is built around);
* in event file `26.csv` the identical rows are `train`.

Neither is wrong. The flag answers "is this row inside *this event's* evaluation
window?", and that question has a different answer for each event.

**Consequence:** the aggregate split quoted in Phase 1 - 1,146,154 train (95.77%) /
50,593 prediction (4.23%) - is not a split of the dataset. It is a sum over 22
overlapping windows in which most rows are counted several times. It cannot be used as
a train/test split, and the percentages do not describe any real partition of the data.

---

## 3. Behaviour within each event window

Within a single event file the field is perfectly well-behaved. Checked for all 22 files:

| Property | Result |
|---|---|
| Every event window contains both `train` and `prediction` rows | **22 / 22** |
| Every `prediction` row is strictly later than every `train` row | **22 / 22** |
| The `prediction` block terminates the window (no train rows after it) | **22 / 22** |
| The `prediction` block fully contains the labelled event period | **22 / 22** |

So *within an event window* the design is a clean, leakage-free chronological holdout:
a long normal-history `train` prefix, followed by a short `prediction` window that
contains the labelled event.

See `reports/figures/fig4_train_prediction_layout.png`.

### Per-event breakdown

| event_id | turbine | label | n_train | n_prediction | % prediction | prediction lead before event_start |
|---|---|---|---|---|---|---|
| 0 | A0 | anomaly | 52,148 | 2,838 | 5.16% | 48.0 h |
| 3 | A10 | normal | 52,185 | 3,302 | 5.95% | 0.0 h |
| 10 | A10 | anomaly | 52,323 | 1,269 | 2.37% | 48.0 h |
| 13 | A21 | normal | 50,427 | 3,583 | 6.63% | 72.0 h |
| 14 | A13 | normal | 52,296 | 1,901 | 3.51% | 48.0 h |
| 17 | A10 | normal | 52,309 | 2,781 | 5.05% | 48.0 h |
| 22 | A21 | anomaly | 51,888 | 1,148 | 2.16% | 0.0 h |
| 24 | A0 | normal | 52,289 | 2,714 | 4.93% | 72.0 h |
| 25 | A11 | normal | 52,289 | 2,423 | 4.43% | 0.0 h |
| 26 | A0 | anomaly | 52,261 | 1,441 | 2.68% | 0.0 h |
| 38 | A13 | normal | 52,291 | 2,544 | 4.64% | 72.0 h |
| 40 | A10 | anomaly | 51,219 | 4,939 | 8.79% | 24.0 h |
| 42 | A10 | anomaly | 52,303 | 1,583 | 2.94% | 0.0 h |
| 45 | A13 | anomaly | 52,299 | 1,440 | 2.68% | 72.0 h |
| 51 | A21 | anomaly | 52,043 | 2,393 | 4.40% | 48.0 h |
| 68 | A11 | anomaly | 52,063 | 2,295 | 4.22% | 0.0 h |
| 69 | A11 | normal | 52,220 | 2,593 | 4.73% | 24.0 h |
| 71 | A0 | normal | 52,295 | 2,449 | 4.47% | 24.0 h |
| 72 | A21 | anomaly | 52,065 | 2,017 | 3.73% | 72.0 h |
| 73 | A0 | anomaly | 52,313 | 1,729 | 3.20% | 72.0 h |
| 84 | A13 | anomaly | 52,335 | 1,437 | 2.67% | 48.0 h |
| 92 | A11 | normal | 52,293 | 1,774 | 3.28% | 0.0 h |

The `train` block is remarkably uniform - almost every window has ~52,300 train rows
(~363 days at 10-minute resolution). The windows were evidently constructed to a fixed
recipe: roughly one year of history, then a short evaluation window.

---

## 4. Distribution by turbine and over time

Every turbine carries four or five event windows and therefore both categories:

| Turbine | Event windows | Anomaly / Normal |
|---|---|---|
| A0 | 5 (0, 24, 26, 71, 73) | 3 / 2 |
| A10 | 5 (3, 10, 17, 40, 42) | 3 / 2 |
| A11 | 4 (25, 68, 69, 92) | 1 / 3 |
| A13 | 4 (14, 38, 45, 84) | 2 / 2 |
| A21 | 4 (13, 22, 51, 72) | 3 / 1 |

Chronologically, **`prediction` rows are not globally later than `train` rows.** They
are only locally later, inside their own window. Because window 17 (A10) runs to
2023-11-20 while window 40 (A10) ends 2023-01-26, a `prediction` row from window 40
(January 2023) is chronologically *earlier* than a `train` row from window 17
(November 2023). Pooling all `prediction` rows into a global test set would therefore
train on the future and test on the past for many rows.

---

## 5. Conclusion and Phase 3 decision

| Question | Answer |
|---|---|
| What does `train_test` mean? | **Not documented.** Empirically: the benchmark's per-event evaluation flag. |
| Is it a property of an observation? | **No.** 38,406 timestamps carry both values. |
| Are prediction rows chronologically after training rows? | **Within a window, yes (22/22). Globally, no.** |
| Does every turbine contain both categories? | **Yes, 5/5.** |
| Can it be used as our ML train/test split? | **No.** |

**Decision carried into Phase 3:** `train_test` will be retained as *event-window
metadata* on `analysis_data/scada_by_event.parquet` and used to reproduce the
benchmark's own protocol if we choose to. It will **not** be used as the project's
train/test split, it will **not** be treated as a per-observation attribute, and it
must **not** enter the feature matrix. It is deliberately excluded from
`analysis_data/scada_unique.parquet` for exactly this reason.

The split actually to be used is specified in `reports/phase2_understanding_report.md`.

---

## 6. Reproduction

```
python src/build_analysis_base.py
python src/analyze_phase2.py
```

Outputs: `analysis_data/train_test_by_event.csv`, `analysis_data/phase2_stats.json`.
