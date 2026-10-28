# Pre-Failure SCADA Behaviour - Wind Farm A (Phase 2, Task 5)

Exploratory analysis produced by `src/analyze_pre_failure.py`.
**This is exploratory only. No feature engineering, no feature selection, no target.**

---

## 1. Question and method

**Question:** does sensor behaviour change *before* a documented anomaly, and does it
change more than before a documented *normal* event?

The second half of that question is the important one. Almost any sensor will look
"different" in the hours before a failure if you compare it only to a distant baseline,
because season, load and weather all drift. The 10 `normal` events exist precisely to
control for this, and this analysis uses them as a **control group** throughout.

### Design

| Choice | Value | Why |
|---|---|---|
| Pre-event windows | 1 h, 6 h, 12 h, 24 h, 72 h, 168 h before `event_start` | Covers the horizons requested, plus 3 d and 7 d. |
| Baseline | 90 d to 30 d before `event_start`, same turbine | Recent enough to reflect the machine's condition, far enough to precede any fault. |
| Observation filter | **`status_type_id == 0` only** | Status 4 covers 95% of anomaly-event time. Including it would just re-detect the shutdown - a consequence of failure, not a precursor. |
| Load normalisation | Power-binned residual: sensor value minus the baseline mean *in the same power bin* | Turbine temperatures track load. A raw temperature delta mostly measures how windy it was. |
| Scale | Residual divided by the baseline standard deviation (z) | Comparable across sensors. |
| Test | Mann-Whitney U, anomaly vs normal, with Bonferroni correction over the 20 sensors | Small samples, no normality assumption. |

Sensors examined (20, all documented): gearbox bearing and oil temperature, both
generator bearing temperatures, three stator winding temperatures, three HV transformer
temperatures, hydraulic group oil temperature, nacelle / split-ring / nose-cone /
ambient temperature, grid power, generator and rotor rpm, pitch-angle std dev, wind speed.

---

## 2. The finding that dominates everything else

**Most anomalies have no normal-operation data before `event_start` at all.**

| Pre-event window | Anomaly events with usable status-0 data | Normal events |
|---|---|---|
| 1 h | **3 of 12** | 10 of 10 |
| 6 h | **3 of 12** | 10 of 10 |
| 12 h | **3 of 12** | 10 of 10 |
| 24 h | **3 of 12** | 10 of 10 |
| 72 h | **4 of 12** | 10 of 10 |
| 168 h (7 d) | **4 of 12** | 10 of 10 |

The reason is in `reports/status_analysis.md` section 4.3: for 8 of the 12 anomalies the
turbine is already in status 4 for a full 7 days before `event_start`. There is no
"healthy operation shortly before failure" to analyse, because by the dataset's own
status coding the machine was no longer operating normally.

Independently, from the prediction windows:

* **4 of 12** anomalies have **zero** prediction-window rows before `event_start`.
* **10 of 12** anomalies have **zero status-0** prediction-window rows before `event_start`.
* Prediction-window lead time: **0-72 h, median 48 h.**

See the right-hand panel of `reports/figures/fig5_pre_event_drift.png`.

---

## 3. Results at each horizon

Mean power-binned residual z, anomaly vs the normal control. Positive = higher than the
turbine's own baseline at the same load.

### 24 hours before event_start (3 anomalies vs 10 normals)

| Sensor | Documented meaning | anomaly z | normal z | \|diff\| |
|---|---|---|---|---|
| sensor_38_avg | HV transformer temp L1 | +0.75 | -0.13 | 0.88 |
| **sensor_0_avg** | **Ambient temperature** | **+1.15** | **+0.48** | **0.67** |
| **sensor_53_avg** | **Nose cone temperature** | **+1.10** | **+0.47** | **0.63** |
| sensor_39_avg | HV transformer temp L2 | +0.54 | -0.04 | 0.58 |
| sensor_40_avg | HV transformer temp L3 | +0.37 | -0.17 | 0.53 |
| sensor_43_avg | Nacelle temperature | +0.79 | +0.26 | 0.53 |
| sensor_12_avg | Gearbox oil temperature | +0.46 | +0.11 | 0.35 |
| sensor_11_avg | Gearbox bearing temp (HSS) | +0.25 | +0.06 | 0.19 |

**The two largest absolute anomaly signals are ambient temperature and nose-cone
temperature.** Neither is a fault precursor - they are seasonal. The nose cone tracks
ambient almost exactly. Their presence at the top of the list is the clearest possible
evidence that this ranking is dominated by *when in the year the event happened*, not by
machine condition.

### 72 hours and 7 days before event_start (4 anomalies vs 10 normals)

At 72 h the pattern is similar but weaker (largest \|diff\| 0.69, HV transformer L1).
At 168 h it **reverses**: anomaly z values go slightly *negative* while normal z values
stay positive, giving a largest \|diff\| of 0.48 on nacelle temperature. A signal that
changes sign with horizon is characteristic of noise, not of a developing fault.

### 1-12 hours before event_start

The apparent separation is largest at 1 h (HV transformer L1, \|diff\| = 1.29). But this
rests on the same 3 anomaly events, each contributing about 6 observations, and a 1-hour
lead time has no maintenance value. It is reported for completeness only.

---

## 4. Statistical testing

Mann-Whitney U, anomaly vs normal, over 20 sensors at each horizon:

| Horizon | n anomaly | n normal | Sensors tested | p < 0.05 uncorrected | **Surviving Bonferroni (alpha = 0.0025)** |
|---|---|---|---|---|---|
| 24 h | 3 | 10 | 20 | 1 (sensor_39_avg, p = 0.049) | **0** |
| 72 h | 4 | 10 | 20 | 0 | **0** |
| 168 h | 4 | 10 | 20 | 0 | **0** |

**No sensor separates anomaly events from normal events at any horizon once multiple
comparisons are accounted for.** The single uncorrected hit at 24 h (HV transformer
phase L2, p = 0.049) is exactly what one expects by chance when testing 20 sensors.

These sample sizes are near the floor of what the test can resolve. With **3**
anomalies against 10 normals, the smallest two-sided p-value obtainable - even from a
flawless, exceptionless separation - is 2 / C(13,3) = **0.00699**, which is *above* the
Bonferroni threshold of 0.0025. **At the 24 h horizon a corrected-significant result is
arithmetically impossible, whatever the effect size.** With **4** anomalies it is
2 / C(14,4) = **0.00200**, which clears the threshold only just, and only if the
separation is perfect.

So the honest reading is: this analysis **fails to demonstrate** a pre-event precursor,
and at these sample sizes it is barely capable of demonstrating one. That is a limit of
the available labelled data - not evidence that no precursor exists in wind turbine
physics generally.

---

## 5. Per-event view (24 h horizon)

Top three sensors by absolute residual z for each event that has data:

| Event | Turbine | Label | Description | Top sensors |
|---|---|---|---|---|
| 0 | A0 | anomaly | Generator bearing failure | ambient +2.71, nose cone +2.51, nacelle +1.68 |
| 40 | A10 | anomaly | Generator bearing failure | ambient -0.94, grid power +0.91, nose cone -0.86 |
| 68 | A11 | anomaly | Transformer failure | ambient +1.69, nose cone +1.65, nacelle +1.15 |
| 13 | A21 | normal | | split ring +1.98, nacelle +1.69, gen bearing 2 +1.58 |
| 25 | A11 | normal | | ambient +1.78, nose cone +1.75, nacelle +0.78 |
| 17 | A10 | normal | | ambient -1.52, HV transf L1 -1.26, nose cone -1.25 |
| 92 | A11 | normal | | ambient +1.24, nose cone +1.01, gen bearing 2 +0.99 |
| 24 | A0 | normal | | nose cone +1.10, ambient +0.87, gen bearing 2 -0.53 |

Two things stand out:

1. **Normal event 13 (A21) shows a larger deviation (+1.98) than either generator
   bearing failure.** If these z-scores were a health indicator, event 13 would be the
   most alarming window in the dataset - and it is a confirmed healthy period.
2. **The two Generator bearing failures disagree in sign.** Event 0 shows ambient
   +2.71; event 40 shows ambient -0.94. The same named failure mode produces opposite
   signatures, because the signature is seasonal (August vs December), not physical.

Notably, for both Generator bearing failures the *generator bearing* temperatures
(sensor_13_avg / sensor_14_avg) are **not** among the top three sensors - the physically
expected precursor does not lead the ranking.

---

## 6. Sensor behaviour around events (visual check)

`reports/figures/fig3_sensors_around_events.png` plots generator bearing temperatures
(drive end and non-drive end) with ambient temperature for the two Generator bearing
failures, from 30 days before to 5 days after `event_start`.

The visible temperature excursions occur **at and after** `event_start`, inside the
status-4 period. There is no clear, sustained divergence from ambient in the days before
`event_start` in either event.

---

## 7. Conclusion

| Question | Answer |
|---|---|
| Can event timestamps be aligned with SCADA observations? | **Yes, 22/22** (see `reports/event_analysis.md`). |
| Is there measurable sensor drift before documented anomalies? | **Not demonstrable with this data.** |
| Does any sensor separate anomalies from the normal control group? | **No** - nothing survives correction at any horizon. |
| Is the apparent 24 h "signal" real? | **No.** It is led by ambient and nose-cone temperature (seasonal), reverses sign at 7 days, and is exceeded by a confirmed-healthy control window. |
| Why is the evidence so thin? | **10 of 12 anomalies have no normal-operation data before `event_start`.** |

**This does not mean the dataset is unusable.** It means one specific framing is
unusable: supervised learning of a *"failure within the next N hours"* target from
pre-event SCADA data. There are not enough pre-event observations, and the labelled
horizon (0-72 h) is far too short to support the "estimated lead time before failure"
dashboard item.

What the data *does* support - detecting anomalous behaviour during the prediction
window against a turbine-specific normal-behaviour model, evaluated per event across 12
anomalies and 10 controls - is set out in `reports/potential_pm_signals.md` and
`reports/phase2_understanding_report.md`.

---

## 8. Reproduction

```
python src/build_analysis_base.py
python src/analyze_pre_failure.py
python src/explore_data.py
```

Outputs: `analysis_data/pre_event_drift.csv` (raw deltas, power-binned residuals and
z-scores for all 20 sensors x 6 horizons x 22 events), `pre_event_z_by_label.csv`,
`status_onset.csv`.
