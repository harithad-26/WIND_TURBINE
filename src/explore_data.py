"""
Phase 2 - Exploratory visualisation for Wind Farm A.

Produces a small set of interpretable figures in reports/figures/.
Every figure is driven by the corrected analysis base, never by the Phase 1
master (which contains 64.5% duplicate rows).

Reads : analysis_data/scada_unique.parquet, analysis_data/scada_by_event.parquet,
        analysis_data/event_index.csv, analysis_data/pre_event_drift.csv
Writes: reports/figures/*.png
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AD, FIG = "analysis_data", os.path.join("reports", "figures")
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False,
                     "axes.spines.right": False})

STATUS_COLOR = {0: "#2E7D32", 3: "#F9A825", 4: "#C62828"}
STATUS_NAME = {0: "status 0", 3: "status 3", 4: "status 4"}


def load():
    u = pd.read_parquet(os.path.join(AD, "scada_unique.parquet"))
    ev = pd.read_csv(os.path.join(AD, "event_index.csv"), sep=";",
                     parse_dates=["event_start_aligned", "event_end_aligned",
                                  "pred_start", "pred_end"])
    ev = ev.rename(columns={"event_start_aligned": "s", "event_end_aligned": "e"})
    ev["desc"] = ev.event_description.fillna("")
    return u.sort_values(["turbine_uid", "time_stamp"]), ev


def fig1_status(u):
    """Status distribution overall and per turbine."""
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    vc = u.status_type_id.value_counts().sort_index()
    ax[0].bar([STATUS_NAME[c] for c in vc.index], vc.values,
              color=[STATUS_COLOR[c] for c in vc.index])
    for i, v in enumerate(vc.values):
        ax[0].text(i, v, "{:,}\n{:.2f}%".format(v, v / len(u) * 100),
                   ha="center", va="bottom", fontsize=8)
    ax[0].set_ylabel("observations")
    ax[0].set_title("status_type_id distribution\n(deduplicated, {:,} obs)".format(len(u)))
    ax[0].set_ylim(0, vc.max() * 1.22)

    ct = pd.crosstab(u.turbine_uid, u.status_type_id, normalize="index") * 100
    bottom = np.zeros(len(ct))
    for c in ct.columns:
        ax[1].bar(ct.index, ct[c], bottom=bottom, color=STATUS_COLOR[c],
                  label=STATUS_NAME[c])
        bottom += ct[c].values
    ax[1].set_ylabel("% of observations")
    ax[1].set_title("status_type_id share by turbine")
    ax[1].legend(fontsize=8, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.32))
    fig.suptitle("Figure 1 - Operating-status distribution (meaning of codes NOT documented)",
                 fontsize=10, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig1_status_distribution.png"), bbox_inches="tight")
    plt.close(fig)


def fig2_timeline(u, ev):
    """Per-turbine timeline of status plus labelled events - the key overview."""
    turbines = sorted(u.turbine_uid.unique())
    fig, axes = plt.subplots(len(turbines), 1, figsize=(12, 1.55 * len(turbines)),
                             sharex=True)
    for ax, t in zip(axes, turbines):
        g = u[u.turbine_uid == t]
        for c in (0, 3, 4):
            s = g[g.status_type_id == c]
            ax.plot(s.time_stamp, np.full(len(s), 0.5), "|", color=STATUS_COLOR[c],
                    markersize=9, alpha=0.85)
        for _, e in ev[ev.turbine_uid == t].iterrows():
            anom = e.event_label == "anomaly"
            ax.axvspan(e.s, e.e, ymin=0.62, ymax=1.0,
                       color="#B71C1C" if anom else "#1565C0", alpha=0.55)
            ax.text(e.s, 1.06, "{}{}".format(e.event_id,
                    "" if not anom else " " + e.desc.split()[0]),
                    fontsize=6, rotation=0, ha="left",
                    color="#B71C1C" if anom else "#1565C0")
        ax.set_ylim(0, 1.25)
        ax.set_yticks([])
        ax.set_ylabel(t, rotation=0, ha="right", va="center", fontsize=9)
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    handles = [plt.Line2D([], [], color=STATUS_COLOR[c], lw=4, label=STATUS_NAME[c])
               for c in (0, 3, 4)]
    handles += [plt.Rectangle((0, 0), 1, 1, color="#B71C1C", alpha=0.55, label="anomaly event"),
                plt.Rectangle((0, 0), 1, 1, color="#1565C0", alpha=0.55, label="normal event")]
    axes[0].legend(handles=handles, fontsize=7, ncol=5, loc="upper center",
                   bbox_to_anchor=(0.5, 2.05))
    fig.suptitle("Figure 2 - Status timeline and labelled events per turbine "
                 "(aligned timestamps)", fontsize=10, y=1.0)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig2_status_event_timeline.png"), bbox_inches="tight")
    plt.close(fig)


def fig3_event_sensors(u, ev):
    """Documented sensors around two anomalies with usable pre-event data."""
    picks = [(0, "A0", ["sensor_13_avg", "sensor_14_avg"],
              "Generator bearing temps (DE / NDE)"),
             (40, "A10", ["sensor_13_avg", "sensor_14_avg"],
              "Generator bearing temps (DE / NDE)")]
    fig, axes = plt.subplots(len(picks), 1, figsize=(11, 3.1 * len(picks)))
    for ax, (eid, t, cols, title) in zip(np.atleast_1d(axes), picks):
        e = ev[ev.event_id == eid].iloc[0]
        g = u[(u.turbine_uid == t)
              & (u.time_stamp >= e.s - pd.Timedelta(days=30))
              & (u.time_stamp <= e.e + pd.Timedelta(days=5))]
        for c in cols:
            ax.plot(g.time_stamp, g[c], lw=0.7, label=c)
        ax.plot(g.time_stamp, g.sensor_0_avg, lw=0.7, color="grey",
                alpha=0.7, label="sensor_0_avg (ambient)")
        ax.axvspan(e.s, e.e, color="#B71C1C", alpha=0.12)
        ax.axvline(e.s, color="#B71C1C", lw=1.2, ls="--")
        ax.axvline(e.pred_start, color="#1565C0", lw=1.0, ls=":")
        ax.text(e.pred_start, ax.get_ylim()[1], " prediction window starts",
                fontsize=7, color="#1565C0", va="top")
        ax.set_title("Event {} on {} - {} - {}  (30 days before -> 5 days after)".format(
            eid, t, e.desc, title), fontsize=9)
        ax.set_ylabel("degC")
        ax.legend(fontsize=7, ncol=4)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    fig.suptitle("Figure 3 - Sensor behaviour around documented anomalies "
                 "(dashed red = event_start)", fontsize=10, y=1.0)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig3_sensors_around_events.png"), bbox_inches="tight")
    plt.close(fig)


def fig4_train_pred(ev):
    """Train/prediction split is per event window, and prediction always ends it."""
    d = pd.read_parquet(os.path.join(AD, "scada_by_event.parquet"),
                        columns=["event_id", "time_stamp_aligned", "train_test"])
    order = ev.sort_values(["turbine_uid", "s"]).event_id.tolist()
    fig, ax = plt.subplots(figsize=(11, 5.2))
    for i, eid in enumerate(order):
        g = d[d.event_id == eid]
        tr, pr = g[g.train_test == "train"], g[g.train_test == "prediction"]
        ax.hlines(i, tr.time_stamp_aligned.min(), tr.time_stamp_aligned.max(),
                  color="#90A4AE", lw=5)
        ax.hlines(i, pr.time_stamp_aligned.min(), pr.time_stamp_aligned.max(),
                  color="#EF6C00", lw=5)
        e = ev[ev.event_id == eid].iloc[0]
        ax.plot([e.s], [i], marker="v", ms=6,
                color="#B71C1C" if e.event_label == "anomaly" else "#1565C0")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(["ev{} {}".format(e, ev[ev.event_id == e].turbine_uid.iloc[0])
                        for e in order], fontsize=7)
    ax.set_xlabel("aligned time")
    handles = [plt.Line2D([], [], color="#90A4AE", lw=5, label="train"),
               plt.Line2D([], [], color="#EF6C00", lw=5, label="prediction"),
               plt.Line2D([], [], color="#B71C1C", marker="v", ls="", label="anomaly start"),
               plt.Line2D([], [], color="#1565C0", marker="v", ls="", label="normal start")]
    ax.legend(handles=handles, fontsize=8, ncol=4, loc="upper left")
    ax.set_title("Figure 4 - train_test is a per-event-window label; the prediction\n"
                 "window always terminates the window and contains the labelled event",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig4_train_prediction_layout.png"), bbox_inches="tight")
    plt.close(fig)


def fig5_pre_event(ev):
    """The negative result: anomaly drift is not separable from the normal control."""
    pre = pd.read_csv(os.path.join(AD, "pre_event_drift.csv"))
    zc = [c for c in pre.columns if c.startswith("z_")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))

    w = pre[pre.window_h == 24]
    m = w.groupby("label")[zc].mean().T
    m.index = [i[2:] for i in m.index]
    m = m.sort_values("anomaly")
    y = np.arange(len(m))
    axes[0].barh(y - 0.2, m.get("anomaly", 0), 0.4, color="#C62828", label="anomaly (n=3)")
    axes[0].barh(y + 0.2, m.get("normal", 0), 0.4, color="#1565C0", label="normal (n=10)")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(m.index, fontsize=7)
    axes[0].axvline(0, color="k", lw=0.8)
    axes[0].set_xlabel("mean power-binned residual (z)")
    axes[0].set_title("24 h before event_start\n(status 0 observations only)", fontsize=9)
    axes[0].legend(fontsize=7)

    cov = pre.groupby(["window_h", "label"]).event_id.nunique().unstack().fillna(0)
    axes[1].plot(cov.index, cov["anomaly"], "o-", color="#C62828", label="anomaly events")
    axes[1].plot(cov.index, cov["normal"], "o-", color="#1565C0", label="normal events")
    axes[1].axhline(12, color="#C62828", ls=":", lw=1)
    axes[1].axhline(10, color="#1565C0", ls=":", lw=1)
    axes[1].set_xscale("log")
    axes[1].set_xticks([1, 6, 12, 24, 72, 168])
    axes[1].set_xticklabels(["1h", "6h", "12h", "24h", "72h", "7d"])
    axes[1].set_ylabel("events with usable data")
    axes[1].set_xlabel("pre-event window")
    axes[1].set_title("Only 3-4 of 12 anomalies have ANY normal-operation\n"
                      "data before event_start (dotted = total available)", fontsize=9)
    axes[1].legend(fontsize=7)
    fig.suptitle("Figure 5 - Pre-event behaviour: no sensor separates anomalies from the "
                 "normal control group", fontsize=10, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig5_pre_event_drift.png"), bbox_inches="tight")
    plt.close(fig)


def fig6_leakage(u, ev):
    """status_type_id vs the event label - the leakage picture."""
    u = u.copy()
    u["in_anom"] = False
    for _, e in ev[ev.event_label == "anomaly"].iterrows():
        u.loc[(u.turbine_uid == e.turbine_uid) & (u.time_stamp >= e.s)
              & (u.time_stamp <= e.e), "in_anom"] = True
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    ct = pd.crosstab(u.status_type_id, u.in_anom)
    ct.columns = ["outside anomaly", "inside anomaly"]
    ct.plot(kind="bar", ax=ax[0], color=["#90A4AE", "#C62828"], width=0.75)
    ax[0].set_yscale("log")
    ax[0].set_xlabel("status_type_id")
    ax[0].set_ylabel("observations (log)")
    ax[0].set_title("status_type_id vs labelled anomaly periods", fontsize=9)
    ax[0].legend(fontsize=7)
    ax[0].tick_params(axis="x", rotation=0)

    ews = pd.read_csv(os.path.join(AD, "status_within_events.csv"))
    for lab, col in (("anomaly", "#C62828"), ("normal", "#1565C0")):
        s = ews[ews.label == lab]
        ax[1].scatter(s.pct_status_0, s.pct_status_4, color=col, s=40,
                      label="{} events".format(lab), alpha=0.8, edgecolor="w")
    ax[1].set_xlabel("% status 0 inside the event period")
    ax[1].set_ylabel("% status 4 inside the event period")
    ax[1].set_title("Event periods are almost perfectly separated\n"
                    "by status_type_id alone => leakage risk", fontsize=9)
    ax[1].legend(fontsize=7)
    fig.suptitle("Figure 6 - status_type_id is a near-perfect proxy for the event label",
                 fontsize=10, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig6_status_leakage.png"), bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(FIG, exist_ok=True)
    u, ev = load()
    for fn, args in [(fig1_status, (u,)), (fig2_timeline, (u, ev)),
                     (fig3_event_sensors, (u, ev)), (fig4_train_pred, (ev,)),
                     (fig5_pre_event, (ev,)), (fig6_leakage, (u, ev))]:
        fn(*args)
        print("  wrote", fn.__name__)
    print("\nFigures written to {}/".format(FIG))


if __name__ == "__main__":
    main()
