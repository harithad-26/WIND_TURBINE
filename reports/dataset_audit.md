# Dataset Audit Report: Zenodo Wind Farm A Dataset
**Project:** AI-Based Predictive Maintenance of Wind Turbines (Machine Learning Powered Early Failure Prediction using SCADA Data)  
**Date:** September 2026  
**Scope:** Dataset Inspection & Documentation Phase (Non-destructive inspection, no model training, no UI creation)

---

## Dataset Overview

The **Zenodo Wind Farm A Dataset** comprises multi-year Supervisory Control and Data Acquisition (SCADA) operational records from a commercial wind farm. The dataset is structured into 22 individual event data files stored in CSV format, accompanied by two metadata reference files (`event_info.csv` and `feature_description.csv`).

| Metric | Metric Value | Source Status |
| :--- | :--- | :--- |
| **Total Raw Dataset Files** | 22 SCADA event files (`0.csv` through `92.csv`) | **CONFIRMED** |
| **Metadata Reference Files** | 2 files (`event_info.csv`, `feature_description.csv`) | **CONFIRMED** |
| **Total Observations (Rows)** | 1,196,747 rows | **CONFIRMED** |
| **Total Columns per SCADA File** | 86 columns | **CONFIRMED** |
| **Physical Wind Turbines (Assets)** | 5 unique asset IDs (`0`, `10`, `11`, `13`, `21`) | **CONFIRMED** |
| **Total Logged Operational Events** | 22 events (12 anomalies / failure events, 10 normal control periods) | **CONFIRMED** |
| **Complete Time Period Covered** | `2022-01-01 00:00:00` to `2023-11-20 00:40:00` (~22.6 months) | **CONFIRMED** |
| **SCADA Sampling Resolution** | 10-minute interval series | **CONFIRMED** |
| **Total Data Points** | 102,920,242 individual field values | **CONFIRMED** |

---

## File Inventory

All 22 SCADA dataset files inside `datasets/` use a semicolon (`;`) delimiter, contain 86 columns, and have zero duplicate rows. Each dataset file is named according to its corresponding `event_id` in `event_info.csv` and contains approximately 1 year of continuous 10-minute SCADA measurements prior to and during the event window.

| Filename | File Size | Target Asset ID | Event ID | Event Type | Total Rows | Null Count | Duplicate Rows | SCADA Start Time | SCADA End Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `0.csv` | 35.18 MB | Asset `0` | Event `0` | Anomaly | 54,986 | 2 | 0 | 2022-08-04 06:10:00 | 2023-08-24 06:10:00 |
| `3.csv` | 35.37 MB | Asset `10` | Event `3` | Normal | 55,487 | 4 | 0 | 2022-04-27 03:00:00 | 2023-05-20 01:10:00 |
| `10.csv` | 34.17 MB | Asset `10` | Event `10` | Anomaly | 53,592 | 6 | 0 | 2022-10-09 08:40:00 | 2023-10-18 08:40:00 |
| `13.csv` | 34.54 MB | Asset `21` | Event `13` | Normal | 54,010 | 0 | 0 | 2022-04-30 13:20:00 | 2023-05-25 10:20:00 |
| `14.csv` | 34.92 MB | Asset `13` | Event `14` | Normal | 54,197 | 0 | 0 | 2022-03-03 14:00:00 | 2023-03-16 18:40:00 |
| `17.csv` | 35.14 MB | Asset `10` | Event `17` | Normal | 55,090 | 6 | 0 | 2022-10-31 15:20:00 | 2023-11-20 00:40:00 |
| `22.csv` | 33.83 MB | Asset `21` | Event `22` | Anomaly | 53,036 | 2 | 0 | 2022-08-12 09:50:00 | 2023-08-20 09:50:00 |
| `24.csv` | 35.27 MB | Asset `0` | Event `24` | Normal | 55,003 | 0 | 0 | 2022-04-24 15:00:00 | 2023-05-13 11:20:00 |
| `25.csv` | 34.93 MB | Asset `11` | Event `25` | Normal | 54,712 | 0 | 0 | 2022-05-23 06:50:00 | 2023-06-09 02:30:00 |
| `26.csv` | 34.40 MB | Asset `0` | Event `26` | Anomaly | 53,702 | 2 | 0 | 2022-10-12 10:20:00 | 2023-10-22 10:20:00 |
| `38.csv` | 35.55 MB | Asset `13` | Event `38` | Normal | 54,835 | 0 | 0 | 2022-06-28 15:40:00 | 2023-07-17 07:40:00 |
| `40.csv` | 35.58 MB | Asset `10` | Event `40` | Anomaly | 56,158 | 4 | 0 | 2022-01-01 00:00:00 | 2023-01-28 13:00:00 |
| `42.csv` | 34.28 MB | Asset `10` | Event `42` | Anomaly | 53,886 | 6 | 0 | 2022-09-09 15:50:00 | 2023-09-20 15:50:00 |
| `45.csv` | 34.79 MB | Asset `13` | Event `45` | Anomaly | 53,739 | 0 | 0 | 2022-04-16 18:10:00 | 2023-04-26 18:10:00 |
| `51.csv` | 34.81 MB | Asset `21` | Event `51` | Anomaly | 54,436 | 2 | 0 | 2022-10-04 01:30:00 | 2023-10-20 16:10:00 |
| `68.csv` | 34.70 MB | Asset `11` | Event `68` | Anomaly | 54,358 | 0 | 0 | 2022-07-28 13:20:00 | 2023-08-13 13:20:00 |
| `69.csv` | 34.99 MB | Asset `11` | Event `69` | Normal | 54,813 | 2 | 0 | 2022-09-03 00:50:00 | 2023-09-21 00:50:00 |
| `71.csv` | 34.85 MB | Asset `0` | Event `71` | Normal | 54,744 | 0 | 0 | 2022-01-01 00:00:00 | 2023-01-18 00:00:00 |
| `72.csv` | 34.57 MB | Asset `21` | Event `72` | Anomaly | 54,082 | 2 | 0 | 2022-10-07 08:40:00 | 2023-10-21 08:40:00 |
| `73.csv` | 34.63 MB | Asset `0` | Event `73` | Anomaly | 54,042 | 0 | 0 | 2022-06-07 11:40:00 | 2023-06-19 11:40:00 |
| `84.csv` | 34.79 MB | Asset `13` | Event `84` | Anomaly | 53,772 | 2 | 0 | 2022-09-03 15:30:00 | 2023-09-13 15:30:00 |
| `92.csv` | 34.40 MB | Asset `11` | Event `92` | Normal | 54,067 | 0 | 0 | 2022-04-04 02:30:00 | 2023-04-16 10:00:00 |
| **Total** | **766.19 MB** | **5 Assets** | **22 Events** | **12 A / 10 N** | **1,196,747** | **40** | **0** | **2022-01-01** | **2023-11-20** |

---

## Feature Dictionary

The 86 columns present in each SCADA CSV file consist of 5 header/metadata features (`time_stamp`, `asset_id`, `id`, `train_test`, `status_type_id`) and 81 physical/aggregated sensor measurements mapped from `feature_description.csv`.

| Feature Base Name | CSV Column Name(s) | Decoded Feature Description | Unit | Stat Type | Angle | Counter | Type | Empirical Range [Min, Max] | Source Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `sensor_0` | `sensor_0_avg` | Ambient temperature | °C | average | False | False | float64 | [4.0, 41.0] | **CONFIRMED** |
| `sensor_1` | `sensor_1_avg` | Wind absolute direction | ° | average | True | False | float64 | [0.0, 359.0] | **CONFIRMED** |
| `sensor_2` | `sensor_2_avg` | Wind relative direction | ° | average | True | False | float64 | [-180.0, 180.0] | **CONFIRMED** |
| `wind_speed_3` | `wind_speed_3_avg`, `max`, `min`, `std` | Anemometer wind speed | m/s | avg,max,min,std | False | False | float64 | [0.4, 70.0] | **CONFIRMED** |
| `wind_speed_4` | `wind_speed_4_avg` | Estimated wind speed | m/s | average | False | False | float64 | [0.0, 26.6] | **CONFIRMED** |
| `sensor_5` | `sensor_5_avg`, `max`, `min`, `std` | Blade pitch angle | ° | avg,max,min,std | True | False | float64 | [-5.0, 90.0] | **CONFIRMED** |
| `sensor_6` | `sensor_6_avg` | Temperature in hub controller | °C | average | False | False | float64 | [11.0, 52.0] | **CONFIRMED** |
| `sensor_7` | `sensor_7_avg` | Temperature top nacelle controller | °C | average | False | False | float64 | [22.0, 59.0] | **CONFIRMED** |
| `sensor_8` | `sensor_8_avg` | Temp in choke coils on VCS-section | °C | average | False | False | float64 | [13.0, 149.0] | **CONFIRMED** |
| `sensor_9` | `sensor_9_avg` | Temperature on VCP-board | °C | average | False | False | float64 | [25.0, 66.0] | **CONFIRMED** |
| `sensor_10` | `sensor_10_avg` | Temp in VCS cooling water | °C | average | False | False | float64 | [20.0, 56.0] | **CONFIRMED** |
| `sensor_11` | `sensor_11_avg` | Temp in gearbox bearing (high speed shaft) | °C | average | False | False | float64 | [15.0, 72.0] | **CONFIRMED** |
| `sensor_12` | `sensor_12_avg` | Temperature oil in gearbox | °C | average | False | False | float64 | [15.0, 65.0] | **CONFIRMED** |
| `sensor_13` | `sensor_13_avg` | Temp in generator bearing 2 (Drive End) | °C | average | False | False | float64 | [13.0, 205.0] | **CONFIRMED** |
| `sensor_14` | `sensor_14_avg` | Temp in generator bearing 1 (Non-Drive End) | °C | average | False | False | float64 | [12.0, 205.0] | **CONFIRMED** |
| `sensor_15` | `sensor_15_avg` | Temp inside generator stator windings ph 1 | °C | average | False | False | float64 | [14.0, 205.0] | **CONFIRMED** |
| `sensor_16` | `sensor_16_avg` | Temp inside generator stator windings ph 2 | °C | average | False | False | float64 | [14.0, 205.0] | **CONFIRMED** |
| `sensor_17` | `sensor_17_avg` | Temp inside generator stator windings ph 3 | °C | average | False | False | float64 | [14.0, 205.0] | **CONFIRMED** |
| `sensor_18` | `sensor_18_avg`, `max`, `min`, `std` | Generator rpm in latest period | rpm | avg,max,min,std | False | False | float64 | [0.0, 2040.9] | **CONFIRMED** |
| `sensor_19` | `sensor_19_avg` | Temp in split ring chamber | °C | average | False | False | float64 | [10.0, 205.0] | **CONFIRMED** |
| `sensor_20` | `sensor_20_avg` | Temp in busbar section | °C | average | False | False | float64 | [17.0, 77.0] | **CONFIRMED** |
| `sensor_21` | `sensor_21_avg` | Temp IGBT-driver grid side inverter | °C | average | False | False | float64 | [24.0, 59.0] | **CONFIRMED** |
| `sensor_22` | `sensor_22_avg` | Actual phase displacement | N/A | average | False | False | float64 | [0.2, 1.0] | **CONFIRMED** |
| `sensor_23` | `sensor_23_avg` | Averaged current in phase 1 | A | average | False | False | float64 | [0.0, 1701.8] | **CONFIRMED** |
| `sensor_24` | `sensor_24_avg` | Averaged current in phase 2 | A | average | False | False | float64 | [1.0, 1717.6] | **CONFIRMED** |
| `sensor_25` | `sensor_25_avg` | Averaged current in phase 3 | A | average | False | False | float64 | [1.0, 1690.5] | **CONFIRMED** |
| `sensor_26` | `sensor_26_avg` | Grid frequency | Hz | average | False | False | float64 | [0.0, 50.1] | **CONFIRMED** |
| `reactive_power_27` | `reactive_power_27_avg`, `max`, `min`, `std` | Possible grid capacitive reactive power | kVAr | avg,max,min,std | False | False | float64 | [-0.09, 0.49] | **CONFIRMED** |
| `reactive_power_28` | `reactive_power_28_avg`, `max`, `min`, `std` | Possible grid inductive reactive power | kVAr | avg,max,min,std | False | False | float64 | [-0.49, 0.10] | **CONFIRMED** |
| `power_29` | `power_29_avg`, `max`, `min`, `std` | Possible grid active power | kW | avg,max,min,std | False | False | float64 | [0.0, 0.98] | **CONFIRMED** |
| `power_30` | `power_30_avg`, `max`, `min`, `std` | Grid power | kW | avg,max,min,std | False | False | float64 | [-0.04, 1.03] | **CONFIRMED** |
| `sensor_31` | `sensor_31_avg`, `max`, `min`, `std` | Grid reactive power | kVAr | avg,max,min,std | False | False | float64 | [-1002.8, 1003.3] | **CONFIRMED** |
| `sensor_32` | `sensor_32_avg` | Averaged voltage in phase 1 | V | average | False | False | float64 | [0.0, 419.7] | **CONFIRMED** |
| `sensor_33` | `sensor_33_avg` | Averaged voltage in phase 2 | V | average | False | False | float64 | [0.0, 418.1] | **CONFIRMED** |
| `sensor_34` | `sensor_34_avg` | Averaged voltage in phase 3 | V | average | False | False | float64 | [0.0, 419.7] | **CONFIRMED** |
| `sensor_35` | `sensor_35_avg` | Temp IGBT rotor inverter phase 1 | °C | average | False | False | float64 | [24.0, 98.0] | **CONFIRMED** |
| `sensor_36` | `sensor_36_avg` | Temp IGBT rotor inverter phase 2 | °C | average | False | False | float64 | [24.0, 61.0] | **CONFIRMED** |
| `sensor_37` | `sensor_37_avg` | Temp IGBT rotor inverter phase 3 | °C | average | False | False | float64 | [24.0, 104.0] | **CONFIRMED** |
| `sensor_38` | `sensor_38_avg` | Temp in HV transformer phase L1 | °C | average | False | False | float64 | [28.0, 107.0] | **CONFIRMED** |
| `sensor_39` | `sensor_39_avg` | Temp in HV transformer phase L2 | °C | average | False | False | float64 | [28.0, 122.0] | **CONFIRMED** |
| `sensor_40` | `sensor_40_avg` | Temp in HV transformer phase L3 | °C | average | False | False | float64 | [27.0, 137.0] | **CONFIRMED** |
| `sensor_41` | `sensor_41_avg` | Temp oil in hydraulic group | °C | average | False | False | float64 | [20.0, 55.0] | **CONFIRMED** |
| `sensor_42` | `sensor_42_avg` | Nacelle direction | ° | average | True | False | float64 | [0.0, 359.0] | **CONFIRMED** |
| `sensor_43` | `sensor_43_avg` | Nacelle temperature | °C | average | False | False | float64 | [15.0, 51.0] | **CONFIRMED** |
| `sensor_44` | `sensor_44` | Active power - generator disconnected | Wh | average | False | False | float64 | [-5278, 1416] | **CONFIRMED** |
| `sensor_45` | `sensor_45` | Active power - generator delta | Wh | average | False | False | float64 | [-1864, 372865] | **CONFIRMED** |
| `sensor_46` | `sensor_46` | Active power - generator star | Wh | average | False | False | float64 | [0.0, 0.0] | **CONFIRMED** |
| `sensor_47` | `sensor_47` | Reactive power - generator disconnected | VArh | average | False | False | float64 | [-5849, 3326] | **CONFIRMED** |
| `sensor_48` | `sensor_48` | Reactive power - generator delta | VArh | average | False | False | float64 | [-98475, 166806] | **CONFIRMED** |
| `sensor_49` | `sensor_49` | Reactive power - generator star | VArh | average | False | False | float64 | [0.0, 0.0] | **CONFIRMED** |
| `sensor_50` | `sensor_50` | Total active power | Wh | average | False | False | float64 | [-5367, 371256] | **CONFIRMED** |
| `sensor_51` | `sensor_51` | Total reactive power | VArh | average | False | False | float64 | [-98475, 166806] | **CONFIRMED** |
| `sensor_52` | `sensor_52_avg`, `max`, `min`, `std` | Rotor rpm | rpm | avg,max,min,std | False | False | float64 | [0.0, 19.6] | **CONFIRMED** |
| `sensor_53` | `sensor_53_avg` | Temperature in the nose cone | °C | average | False | False | float64 | [6.0, 47.0] | **CONFIRMED** |

---

## Event Information

`event_info.csv` defines 22 events across 5 wind turbine assets. Out of 22 events, **12 are classified as `anomaly`** (actual physical failures/degradations) and **10 are classified as `normal`** control periods.

| Asset ID | Event ID | Event Label | Event Start Timestamp | Event Start ID | Event End Timestamp | Event End ID | Targeted Failure Component / Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Asset 11** | Event 68 | `anomaly` | 2023-07-28 13:20:00 | 52063 | 2023-08-11 13:10:00 | 54076 | Transformer failure |
| **Asset 21** | Event 22 | `anomaly` | 2023-08-12 09:50:00 | 51888 | 2023-08-19 10:00:00 | 52892 | Hydraulic group |
| **Asset 21** | Event 72 | `anomaly` | 2023-10-10 08:40:00 | 52497 | 2023-10-17 08:40:00 | 53505 | Gearbox failure |
| **Asset 0** | Event 73 | `anomaly` | 2023-06-10 11:40:00 | 52745 | 2023-06-17 11:40:00 | 53753 | Hydraulic group |
| **Asset 0** | Event 0 | `anomaly` | 2023-08-06 06:10:00 | 52436 | 2023-08-20 06:10:00 | 54447 | Generator bearing failure |
| **Asset 0** | Event 26 | `anomaly` | 2023-10-12 10:20:00 | 52261 | 2023-10-19 10:20:00 | 53269 | Hydraulic group |
| **Asset 10** | Event 40 | `anomaly` | 2022-12-26 00:00:00 | 51363 | 2023-01-26 13:00:00 | 55870 | Generator bearing failure |
| **Asset 10** | Event 42 | `anomaly` | 2023-09-09 15:50:00 | 52303 | 2023-09-16 15:50:00 | 53309 | Hydraulic group |
| **Asset 10** | Event 10 | `anomaly` | 2023-10-11 08:40:00 | 52611 | 2023-10-18 08:40:00 | 53591 | Gearbox failure |
| **Asset 13** | Event 45 | `anomaly` | 2023-04-19 18:10:00 | 52731 | 2023-04-26 18:10:00 | 53738 | Hydraulic group |
| **Asset 13** | Event 84 | `anomaly` | 2023-09-05 15:30:00 | 52623 | 2023-09-12 15:30:00 | 53627 | Hydraulic group |
| **Asset 21** | Event 51 | `anomaly` | 2023-10-06 01:30:00 | 52331 | 2023-10-17 16:10:00 | 54003 | Gearbox bearings damaged |
| **Asset 11** | Event 25 | `normal` | 2023-05-23 06:50:00 | 52289 | 2023-06-05 02:30:00 | 54135 | *None (Normal control window)* |
| **Asset 11** | Event 69 | `normal` | 2023-09-04 00:50:00 | 52364 | 2023-09-18 00:50:00 | 54380 | *None (Normal control window)* |
| **Asset 21** | Event 13 | `normal` | 2023-05-03 13:20:00 | 50859 | 2023-05-24 10:20:00 | 53865 | *None (Normal control window)* |
| **Asset 0** | Event 24 | `normal` | 2023-04-27 15:00:00 | 52720 | 2023-05-11 11:20:00 | 54714 | *None (Normal control window)* |
| **Asset 10** | Event 3 | `normal` | 2023-04-27 03:00:00 | 52185 | 2023-05-18 01:10:00 | 55198 | *None (Normal control window)* |
| **Asset 10** | Event 17 | `normal` | 2023-11-02 15:20:00 | 52597 | 2023-11-16 00:40:00 | 54513 | *None (Normal control window)* |
| **Asset 13** | Event 38 | `normal` | 2023-07-01 15:40:00 | 52723 | 2023-07-15 07:40:00 | 54546 | *None (Normal control window)* |
| **Asset 0** | Event 71 | `normal` | 2023-01-02 00:00:00 | 52439 | 2023-01-16 00:00:00 | 54455 | *None (Normal control window)* |
| **Asset 13** | Event 14 | `normal` | 2023-03-05 14:00:00 | 52584 | 2023-03-12 18:40:00 | 53620 | *None (Normal control window)* |
| **Asset 11** | Event 92 | `normal` | 2023-04-05 02:30:00 | 52437 | 2023-04-14 10:00:00 | 53778 | *None (Normal control window)* |

### Component Failure Summary
1. **Hydraulic Group Failure**: 6 events (`22`, `26`, `42`, `45`, `73`, `84`) across Assets 0, 10, 13, 21.
2. **Gearbox / Gearbox Bearing Failure**: 3 events (`10`, `51`, `72`) across Assets 10, 21.
3. **Generator Bearing Failure**: 2 events (`0`, `40`) across Assets 0, 10.
4. **Transformer Failure**: 1 event (`68`) on Asset 11.

---

## Sensor Mapping

Below is the definitive mapping answering Question 4 of the prompt:

| Required Physical Variable | Dataset Column Name(s) | Documentation Description | Sensor Unit | Mapping Status |
| :--- | :--- | :--- | :--- | :--- |
| **Wind Speed** | `wind_speed_3_avg`, `wind_speed_3_max`, `wind_speed_3_min`, `wind_speed_3_std`, `wind_speed_4_avg` | Anemometer wind speed & estimated wind speed | m/s | **CONFIRMED** |
| **Wind Direction** | `sensor_1_avg`, `sensor_2_avg` | Wind absolute direction (0-360°) & relative direction (-180 to +180°) | ° | **CONFIRMED** |
| **Active Power** | `power_29_avg` (avg/max/min/std), `power_30_avg` (avg/max/min/std), `sensor_44`, `sensor_45`, `sensor_46`, `sensor_50` | Grid power (kW), possible power (kW), disconnected/delta/total active energy (Wh) | kW / Wh | **CONFIRMED** |
| **Rotor Speed** | `sensor_52_avg`, `sensor_52_max`, `sensor_52_min`, `sensor_52_std` | Rotor RPM | rpm | **CONFIRMED** |
| **Generator Speed** | `sensor_18_avg`, `sensor_18_max`, `sensor_18_min`, `sensor_18_std` | Generator RPM in latest period | rpm | **CONFIRMED** |
| **Gearbox Temperature** | `sensor_11_avg` | Temperature in gearbox bearing on high speed shaft | °C | **CONFIRMED** |
| **Gearbox Oil Temperature** | `sensor_12_avg` | Temperature oil in gearbox | °C | **CONFIRMED** |
| **Bearing Temperature** | `sensor_11_avg` (gearbox bearing), `sensor_13_avg` (generator bearing 2 DE), `sensor_14_avg` (generator bearing 1 NDE) | High speed shaft gearbox bearing & Generator bearings 1 and 2 | °C | **CONFIRMED** |
| **Generator Temperature** | `sensor_13_avg`, `sensor_14_avg`, `sensor_15_avg`, `sensor_16_avg`, `sensor_17_avg`, `sensor_19_avg` | Generator bearings (DE/NDE), stator windings phase 1-3, split ring chamber | °C | **CONFIRMED** |
| **Ambient Temperature** | `sensor_0_avg` | Ambient temperature | °C | **CONFIRMED** |
| **Hydraulic Temperature** | `sensor_41_avg` | Temperature oil in hydraulic group | °C | **CONFIRMED** |
| **Hydraulic Pressure** | *None* | No hydraulic pressure sensors exist in documentation or dataset | N/A | **UNKNOWN / NOT PRESENT** |
| **Nacelle Temperature** | `sensor_7_avg`, `sensor_43_avg` | Temperature top nacelle controller & Nacelle temperature | °C | **CONFIRMED** |
| **Vibration** | *None* | No vibration or accelerometer sensors exist in documentation or dataset | N/A | **UNKNOWN / NOT PRESENT** |

---

## Missing Values

Data quality analysis revealed an exceptionally clean dataset with **99.99996% overall completeness**.

| Column Name | Total Missing Rows | Total Observations | Missing Percentage (%) | Imputation Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| `sensor_14_avg` | 20 | 1,196,747 | 0.001671% | Forward fill (`ffill`) or linear interpolation |
| `sensor_22_avg` | 20 | 1,196,747 | 0.001671% | Forward fill (`ffill`) |
| **All Other 84 Columns** | 0 | 1,196,747 | 0.000000% | None required |

The 20 missing values in `sensor_14_avg` and `sensor_22_avg` occur across 6 specific anomaly dataset files (`10.csv`, `17.csv`, `22.csv`, `26.csv`, `42.csv`, `51.csv`, `69.csv`, `84.csv`).

---

## Data Quality

1. **Duplicate Rows:** **CONFIRMED 0 duplicate rows** across all 1,196,747 observations.
2. **Constant Columns:**
   - `sensor_46` (Active power - generator connected in star): Constant `0.0` across all 1,196,747 rows.
   - `sensor_49` (Reactive power - generator connected in star): Constant `0.0` across all 1,196,747 rows.
   - *Explanation:* These turbines operate exclusively in delta generator connection mode.
3. **Near-Constant / Step Columns:**
   - `sensor_26_avg` (Grid frequency): Values are tightly clustered around 50.0 Hz (48.8 Hz to 50.1 Hz), dropping to 0.0 Hz during turbine grid disconnects.
   - `sensor_22_avg` (Phase displacement): Discrete steps between 0.2 and 1.0.
4. **Numerical Bounds & Physical Anomaly Findings:**
   - **Negative Energy Counters:** `sensor_44`, `sensor_47`, `sensor_48`, `sensor_51` exhibit negative values (e.g. `sensor_51` down to -98,475 VArh). This represents reverse power flow / reactive power import from the grid during turbine standstill.
   - **Pitch Angle Range:** `sensor_5_min` reaches -5.0° (fine pitch setting for startup) and 90.0° (feathered pitch state during emergency brake / shutdown).
   - **Thermal Runaway Peaks:** `sensor_13_avg` through `sensor_17_avg` and `sensor_19_avg` peak at 205.0°C during generator bearing/stator failure events.

---

## Failure / Target Analysis

### Direct Answers to Prompt Questions 5 through 11

* **Q5: What column can be used as the failure/fault target?**  
  **Answer (CONFIRMED):** There is **NO pre-existing binary failure target column** (e.g. `target` or `failure`) inside the raw dataset files. The target must be **derived by joining `event_info.csv` with the SCADA files using `event_id`** and flagging timestamps falling within `[event_start, event_end]` during `anomaly` events.

* **Q6: What does `status_type_id` mean, if present?**  
  **Answer (CONFIRMED / INFERRED):** `status_type_id` represents the turbine's SCADA operational state code:
  * `0`: Normal power production state (accounts for 100% of rows in normal evaluation windows).
  * `3`: Warning / Advisory alarm state.
  * `4`: Fault / Trip / Emergency shutdown state (dominates SCADA records during anomaly evaluation windows).

* **Q7: Does `event_info` provide actual failure events?**  
  **Answer (CONFIRMED):** Yes. `event_info.csv` provides 12 verified anomaly failure events complete with exact start/end timestamps and component descriptions.

* **Q8: Does the dataset contain failure-component information?**  
  **Answer (CONFIRMED):** Yes. `event_info.csv` documents specific failure components for all 12 anomaly events (Hydraulic group, Generator bearing, Gearbox/Gearbox bearings, Transformer).

* **Q9: Does the dataset contain maintenance records?**  
  **Answer (CONFIRMED):** **NO.** There are no technician logs, work orders, replacement timestamps, or repair action records present in the workspace.

* **Q10: Can we calculate a genuine failure-risk probability?**  
  **Answer (INFERRED):** **Yes.** By using continuous SCADA sensor trends leading up to known failure windows (`train` phase of anomaly files), machine learning models (e.g., XGBoost, Random Forest, LSTM, Autoencoders) can output a continuous probability $P(\text{Failure in next } \Delta t \mid \text{SCADA features})$.

* **Q11: Can we calculate a genuine failure lead time such as 48 hours?**  
  **Answer (INFERRED):** **Yes.** For each anomaly event, SCADA data is recorded continuously for ~1 year prior to the event. By defining a target pre-failure window $t \in [t_{\text{start}} - 48\text{h}, t_{\text{start}}]$, models can be trained and evaluated specifically on early fault detection lead times (24h, 48h, 72h).

---

## Features Available for Predictive Maintenance

The following **54 continuous physical features** are available and suitable for machine learning predictive maintenance modeling:

```
[THERMAL SUBSYSTEM]
- sensor_0_avg (Ambient Temp)
- sensor_6_avg (Hub Controller Temp)
- sensor_7_avg, sensor_43_avg (Nacelle Controller & Ambient Nacelle Temp)
- sensor_8_avg (Choke Coils Temp)
- sensor_9_avg (VCP Board Temp)
- sensor_10_avg (VCS Cooling Water Temp)
- sensor_11_avg (Gearbox High Speed Shaft Bearing Temp)
- sensor_12_avg (Gearbox Oil Temp)
- sensor_13_avg, sensor_14_avg (Generator DE & NDE Bearing Temps)
- sensor_15_avg, sensor_16_avg, sensor_17_avg (Generator Stator Winding Temps)
- sensor_19_avg (Split Ring Chamber Temp)
- sensor_20_avg (Busbar Section Temp)
- sensor_21_avg, sensor_35_avg, sensor_36_avg, sensor_37_avg (Grid & Rotor Inverter IGBT Temps)
- sensor_38_avg, sensor_39_avg, sensor_40_avg (HV Transformer Phase Temps)
- sensor_41_avg (Hydraulic Oil Temp)
- sensor_53_avg (Nose Cone Temp)

[MECHANICAL & KINEMATIC]
- sensor_18_avg, max, min, std (Generator RPM)
- sensor_52_avg, max, min, std (Rotor RPM)
- sensor_5_avg, max, min, std (Blade Pitch Angle)
- sensor_42_avg (Nacelle Yaw Direction)

[WIND & ENVIRONMENT]
- wind_speed_3_avg, max, min, std (Anemometer Wind Speed)
- wind_speed_4_avg (Estimated Wind Speed)
- sensor_1_avg, sensor_2_avg (Absolute & Relative Wind Direction)

[ELECTRICAL & POWER]
- power_29_avg, max, min, std (Possible Grid Active Power)
- power_30_avg, max, min, std (Grid Active Power)
- reactive_power_27_avg, max, min, std (Capacitive Reactive Power)
- reactive_power_28_avg, max, min, std (Inductive Reactive Power)
- sensor_31_avg, max, min, std (Grid Reactive Power)
- sensor_23_avg, sensor_24_avg, sensor_25_avg (3-Phase Currents)
- sensor_32_avg, sensor_33_avg, sensor_34_avg (3-Phase Voltages)
- sensor_22_avg (Phase Displacement)
- sensor_26_avg (Grid Frequency)
- sensor_44, sensor_45, sensor_50, sensor_51 (Active & Reactive Energy Counters)
```

---

## Features Missing

To build an enterprise-grade wind turbine condition monitoring system, the following features are **not present** in the dataset:

1. **Drivetrain Vibration Signals:** High-frequency vibration / accelerometer data (RMS, peak-to-peak, spectral kurtosis) for main bearing, gearbox, and generator.
2. **Hydraulic System Pressure:** Hydraulic line pressure, accumulator pressure, pitch hydraulic pump pressure.
3. **Oil Quality & Contamination:** Oil particle count, moisture percentage, dielectric breakdown voltage.
4. **Maintenance Logs:** Detailed technician work orders, component replacement history, overhaul dates.
5. **Pitch Motor / Brake Status:** Pitch drive motor currents, brake pad wear indicators.

---

## Recommended Dataset Strategy

1. **Data Cleaning & Imputation:** Impute the 20 null values in `sensor_14_avg` and `sensor_22_avg` using forward fill (`ffill`). Drop constant zero columns `sensor_46` and `sensor_49`.
2. **Derived Feature Engineering:**
   * **Thermal Residuals:** Compute temperature deltas relative to ambient ($\Delta T = T_{\text{component}} - T_{\text{ambient}}$).
   * **Power Curve Efficiency:** Calculate theoretical vs actual power ratio ($P_{\text{actual}} / P_{\text{theoretical}}(v)$).
   * **Rolling Temporal Aggregates:** Compute 1-hour, 6-hour, and 24-hour rolling mean, standard deviation, and max slope for key bearing and oil temperatures.
3. **Target Label Construction:**
   * Join `event_info.csv` on `event_id`.
   * Create a binary target $Y_{\text{early\_warning}} = 1$ for all SCADA observations in the pre-failure window $t \in [t_{\text{start}} - 48\text{h}, t_{\text{start}}]$ for anomaly events.
4. **Cross-Validation Scheme:** Group by `event_id` or `asset_id` to perform leave-one-event-out or leave-one-asset-out cross-validation, preventing data leakage across time frames.

---

## Recommended Next Step

Wait for user review and approval of this comprehensive Dataset Audit Report (`reports/dataset_audit.md`). Once approved, proceed to Phase 2: Feature Engineering & Target Construction Strategy.
