# Potential Predictive-Maintenance Signals - Wind Farm A (Phase 2, Task 6)

Candidate signals identified from **documented sensor meanings only**
(`feature_description.csv`), combined with the event and status analysis.

**No feature has been removed. No statistical feature selection has been performed.**
This is a documented shortlist of what is physically plausible and what data exists to
support it - an input to Phase 3, not a decision made in Phase 2.

---

## 1. What the failure modes require

The 12 documented anomalies span 5 named failure modes. A candidate signal is only
worth listing if a documented sensor plausibly observes the failing subsystem.

| Failure mode | Events | Subsystem | Directly instrumented? |
|---|---|---|---|
| Hydraulic group | 6 | Hydraulic power unit | **Yes** - `sensor_41` (hydraulic group oil temp), plus pitch signals as an indirect actuator proxy |
| Gearbox failure | 2 | Gearbox | **Yes** - `sensor_11`, `sensor_12` |
| Gearbox bearings damaged | 1 | Gearbox bearings | **Partly** - `sensor_11` is the high-speed-shaft bearing only |
| Generator bearing failure | 2 | Generator bearings | **Yes** - `sensor_13` (DE), `sensor_14` (NDE) |
| Transformer failure | 1 | HV transformer | **Yes** - `sensor_38`, `sensor_39`, `sensor_40` |

**Every documented failure mode has at least one directly relevant documented sensor.**
That is a genuinely favourable property of this dataset.

---

## 2. Candidate signals by category

`n` = observations available on the deduplicated base (425,023 total). All units and
descriptions are verbatim from `feature_description.csv`.

### 2.1 Gearbox condition

| Column | Documented meaning | Unit | Why it may be relevant | Data available? |
|---|---|---|---|---|
| `sensor_11_avg` | Temperature in gearbox bearing on high speed shaft | degC | HSS bearing temperature rise above the load-expected value is the standard early indicator of bearing degradation. Directly targets 3 events (2 Gearbox failure + 1 Gearbox bearings damaged). | **Yes**, complete (0 missing) |
| `sensor_12_avg` | Temperature oil in gearbox | degC | Bulk oil temperature responds to increased friction and to cooling-circuit faults. Slower and less specific than bearing temperature, but less noisy. | **Yes**, complete |

### 2.2 Generator condition

| Column | Documented meaning | Unit | Why it may be relevant | Data available? |
|---|---|---|---|---|
| `sensor_13_avg` | Temperature in generator bearing 2 (Drive End) | degC | Directly targets the 2 Generator bearing failures. | **Yes**, complete |
| `sensor_14_avg` | Temperature in generator bearing 1 (Non-Drive End) | degC | As above, opposite end. The DE-NDE *difference* is a classic condition indicator because it cancels ambient and load effects common to both. | **Yes**, 7 missing (0.002%) |
| `sensor_15_avg`, `sensor_16_avg`, `sensor_17_avg` | Temperature inside generator in stator windings phases 1/2/3 | degC | Three-phase symmetry: divergence *between* phases indicates an electrical fault. Balanced rise indicates cooling or overload. | **Yes**, complete |
| `sensor_19_avg` | Temperature in the split ring chamber | degC | Slip-ring / brush-gear condition on a doubly-fed machine. | **Yes**, complete |

### 2.3 Hydraulic system - the largest failure class

| Column | Documented meaning | Unit | Why it may be relevant | Data available? |
|---|---|---|---|---|
| `sensor_41_avg` | Temperature oil in hydraulic group | degC | **The only sensor that directly observes the subsystem responsible for 6 of 12 anomalies.** Rising oil temperature is consistent with internal leakage, pump wear or a failing cooler. Highest-priority candidate on event count alone. | **Yes**, complete |
| `sensor_5_avg/max/min/std` | Pitch angle | deg (angular) | The hydraulic group actuates pitch on this machine type. Degraded hydraulics may show as sluggish or erratic pitch response - `sensor_5_std` within the 10-minute interval is the natural summary. | **Yes**, complete |

### 2.4 Transformer / electrical condition

| Column | Documented meaning | Unit | Why it may be relevant | Data available? |
|---|---|---|---|---|
| `sensor_38_avg`, `sensor_39_avg`, `sensor_40_avg` | Temperature in HV transformer phase L1 / L2 / L3 | degC | Directly targets the 1 Transformer failure. Phase-to-phase imbalance is the meaningful quantity, not absolute temperature. | **Yes**, complete |
| `sensor_23_avg`, `sensor_24_avg`, `sensor_25_avg` | Averaged current in phase 1 / 2 / 3 | A | Current imbalance across phases indicates winding or connection faults. | **Yes**, complete |
| `sensor_32_avg`, `sensor_33_avg`, `sensor_34_avg` | Averaged voltage in phase 1 / 2 / 3 | V | As above, voltage side. | **Yes**, complete |
| `sensor_35_avg`, `sensor_36_avg`, `sensor_37_avg` | Temperature measured by the IGBT-driver on the rotor side inverter phase 1 / 2 / 3 | degC | Converter thermal condition. | **Yes**, complete |
| `sensor_21_avg` | Temperature measured by the IGBT-driver on the grid side inverter | degC | Converter thermal condition, grid side. | **Yes**, complete |
| `sensor_20_avg` | Temperature in the busbar section | degC | Connection/joint heating. | **Yes**, complete |

### 2.5 Rotor and drivetrain behaviour

| Column | Documented meaning | Unit | Why it may be relevant | Data available? |
|---|---|---|---|---|
| `sensor_52_avg/max/min/std` | Rotor rpm | rpm | Speed is required to interpret every temperature. `sensor_52_std` within the interval is a coarse proxy for drivetrain instability. | **Yes**, complete |
| `sensor_18_avg/max/min/std` | Generator rpm in latest period | rpm | As above, generator side. The rotor:generator speed ratio is fixed by the gearbox, so a drift in that ratio would be mechanically meaningful. | **Yes**, complete |

### 2.6 Power behaviour

| Column | Documented meaning | Unit | Why it may be relevant | Data available? |
|---|---|---|---|---|
| `power_30_avg/max/min/std` | Grid power | kW | The load variable. Essential as a *conditioning* variable: every temperature must be interpreted at matched power. Also supports power-curve deviation as an efficiency-loss indicator. | **Yes**, complete |
| `power_29_avg` | Possible grid active power | kW | Documented as *possible* power. The gap between possible and actual power is a curtailment/derating indicator. | **Yes**, complete |
| `sensor_31_avg`, `reactive_power_27/28` | Grid reactive power; possible capacitive / inductive reactive power | kVAr | Reactive-power behaviour relates to generator and converter health. | **Yes**, complete |

### 2.7 Wind and ambient conditions - conditioning variables, not health signals

| Column | Documented meaning | Unit | Role |
|---|---|---|---|
| `wind_speed_3_avg/max/min/std` | Windspeed | m/s | Primary driver of load. Conditioning variable. |
| `wind_speed_4_avg` | Estimated windspeed | m/s | Secondary estimate; disagreement with `wind_speed_3` may indicate anemometer fault. |
| `sensor_0_avg` | Ambient temperature | degC | **Every temperature must be referenced to ambient.** Section 4 explains why this is not optional. |
| `sensor_43_avg` | Nacelle temperature | degC | Internal reference temperature. |
| `sensor_53_avg` | Temperature in the nose cone | degC | Tracks ambient closely; useful as a sanity reference. |
| `sensor_1_avg`, `sensor_2_avg`, `sensor_42_avg` | Wind absolute / relative direction, nacelle direction | deg (angular) | Yaw misalignment (`sensor_2`) affects load. **Angular - must not be averaged or differenced naively; they wrap at 360 deg.** |

### 2.8 Vibration

**Not available. Not documented.** `feature_description.csv` contains no vibration,
acceleration or acoustic channel. Vibration is the standard basis for bearing and
gearbox diagnosis, and its absence is a real limitation: bearing degradation must be
inferred thermally, which is slower and less specific.

---

## 3. Ranked shortlist for Phase 3

Ranked by *number of documented events the signal could plausibly explain*, not by any
statistical criterion.

| Rank | Signal(s) | Events addressed | Justification |
|---|---|---|---|
| 1 | `sensor_41_avg` (+ `sensor_5_std`) | 6 Hydraulic group | Only direct observation of the most common failure mode. |
| 2 | `sensor_13_avg`, `sensor_14_avg` (+ their difference) | 2 Generator bearing | Direct, and the DE-NDE difference is self-normalising. |
| 3 | `sensor_11_avg`, `sensor_12_avg` | 3 Gearbox / gearbox bearing | Direct observation of the gearbox. |
| 4 | `sensor_38/39/40_avg` (+ phase spread) | 1 Transformer | Direct, but a single event. |
| 5 | `sensor_15/16/17_avg` (+ phase spread) | supporting | Generator electrical condition. |
| 6 | `power_30_avg`, `wind_speed_3_avg`, `sensor_0_avg`, `sensor_52_avg`, `sensor_18_avg` | all | **Conditioning variables, mandatory** - see below. |

---

## 4. Two constraints Phase 3 must respect

### 4.1 Raw temperatures are not health signals

Section 3 of `reports/pre_failure_observation_analysis.md` shows what happens if this is
ignored: the strongest apparent "precursor" in the whole dataset turns out to be
**ambient temperature**, and the second is **nose cone temperature**, which simply
tracks ambient. Both are seasonal. A model fed raw temperatures will learn the calendar.

Any temperature-based indicator must therefore be expressed as a **deviation from the
value expected at the same operating point** - conditioned at minimum on power (or wind
speed), rotational speed and ambient temperature. Sensible constructions include
temperature rise over ambient, DE-minus-NDE and phase-to-phase differences (which cancel
common-mode effects), and residuals from a normal-behaviour model.

### 4.2 The evidence for these signals is physical, not empirical

Every signal above is justified by its **documented meaning** and by the failure modes
in `event_info.csv`. **None of them has been shown to separate anomalies from the normal
control group in this dataset** - at 24 h, 72 h or 7 days, nothing survives multiple-
comparison correction, and the sample sizes (3-4 anomalies with usable pre-event data)
cannot support such a demonstration.

This shortlist is therefore a set of **physically motivated hypotheses to be tested in
Phase 3 on the prediction windows**, where all 12 anomalies and all 10 controls have
data. It is not a set of validated predictors, and must not be described as one.

---

## 5. Signals that must be excluded

| Column | Reason |
|---|---|
| `sensor_46`, `sensor_49` | Constant zero across all 1,196,747 raw observations. No information. |
| `status_type_id` | Undocumented meaning; near-perfect proxy for the event label. **Leakage.** Permitted only as a filter for selecting normal-operation training data. |
| `train_test` | Per-event-window metadata, not an observation property. **Leakage.** |
| `row_id_in_event` (raw `id`) | Per-file row counter; correlates with position inside an event window. **Leakage.** |
| `event_id`, `turbine_uid`, `asset_id` | Provenance and grouping keys. Use for splitting and evaluation, never as features. |
| `time_stamp` | Use for ordering and splitting. Raw calendar features risk encoding *when the labelled events happened* rather than machine condition. |

---

## 6. Reproduction

```
python src/make_sensor_mapping.py     # per-column documentation and completeness
python src/analyze_pre_failure.py     # the empirical check behind section 4.2
```

Full per-column detail: `reports/sensor_mapping_report.md`, `analysis_data/sensor_mapping.csv`.
