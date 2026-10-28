"""
WINDGUARD AI — WIND TURBINE CONDITION MONITORING DASHBOARD (app.py)
===================================================================
Enterprise-Grade Industrial AI Dashboard for Wind Turbine Condition Monitoring
and Explainable Anomaly Detection.
"""
import streamlit as st
import pandas as pd
import numpy as np
import textwrap
from pathlib import Path

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="WINDGUARD AI — Industrial Condition Monitoring",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. IMPORTS & DESIGN SYSTEM INJECTION
# -----------------------------------------------------------------------------
from src.dashboard_data import (
    MODEL_MAP, STRATEGY_MAP, REVERSE_STRATEGY_MAP,
    load_best_config, load_model_comparison, load_event_index, load_loeo_folds,
    load_event_scores, load_component_scores, load_attribution_matrix,
    load_feature_ranking, load_event_residuals
)
from src.dashboard_components import (
    inject_custom_css, render_top_navbar, render_fleet_kpis, render_top_filter_bar,
    render_condition_status_panel, plot_component_attribution_percentage,
    plot_actual_vs_expected, plot_zscore_residuals, plot_anomaly_trend,
    plot_aggregation_comparison, render_feature_contribution_table,
    render_maintenance_recommendation
)

import importlib
import src.dashboard_components as dbc
importlib.reload(dbc)

# Inject Enterprise CSS Design System (#F6F8FA background, white cards, subtle shadows)
dbc.inject_custom_css()

# -----------------------------------------------------------------------------
# 3. ENTERPRISE SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
st.sidebar.html("""
<div style="padding: 2px 0 10px 0; border-bottom: 1px solid #1e293b; margin-bottom: 8px;">
    <div style="font-size: 16px; font-weight: 800; color: #ffffff; letter-spacing: -0.2px;">⚡ WINDGUARD AI</div>
    <div style="font-size: 10px; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px;">Condition Monitoring</div>
</div>
<div class="sidebar-section-header">MAIN NAVIGATION</div>
""")

nav_overview = "Overview"
nav_live     = "Live Monitoring"
nav_anomaly  = "Anomaly Events"
nav_comp     = "Component Analysis"
nav_model    = "Model Performance"
nav_history  = "Event History"
nav_how      = "How It Works"
nav_maint    = "Maintenance Guide"
nav_system   = "System Configuration"

NAV_ITEMS = [
    (nav_overview, ":material/dashboard:"),
    (nav_live,     ":material/bolt:"),
    (nav_anomaly,  ":material/warning:"),
    (nav_comp,     ":material/tune:"),
    (nav_model,    ":material/bar_chart:"),
    (nav_history,  ":material/history:"),
    (nav_how,      ":material/info:"),
    (nav_maint,    ":material/build:"),
    (nav_system,   ":material/settings:"),
]

valid_pages = [item[0] for item in NAV_ITEMS]

if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = nav_overview
else:
    # Normalize if previous session state had unicode glyph prefixes
    curr = st.session_state["selected_page"]
    if "  " in curr:
        curr = curr.split("  ")[-1].strip()
    if curr not in valid_pages:
        curr = nav_overview
    st.session_state["selected_page"] = curr

for idx, (label, icon_name) in enumerate(NAV_ITEMS):
    is_active = (st.session_state["selected_page"] == label)
    if st.sidebar.button(
        label,
        key=f"nav_btn_{idx}",
        type="primary" if is_active else "secondary",
        use_container_width=True
    ):
        st.session_state["selected_page"] = label
        st.rerun()

selected_page = st.session_state["selected_page"]

# Render Compact Top Header Bar
render_top_navbar(selected_page)

# -----------------------------------------------------------------------------
# 4. GLOBAL FILTER BAR & DATA RESOLUTION
# -----------------------------------------------------------------------------
selected_farm, model_key, selected_model_name, strategy_key, selected_strategy_name, selected_turbine, selected_event, event_scores_df = render_top_filter_bar(
    MODEL_MAP, STRATEGY_MAP, load_event_scores
)

# Load metadata & models
best_cfg = load_best_config(selected_farm)
event_index_df = load_event_index(selected_farm)
loeo_df = load_loeo_folds(selected_farm)

# Retrieve decision threshold dynamically
threshold_val = float(best_cfg.get("optimal_threshold", 1.0998)) if (model_key == "ridge" and strategy_key == "event_p95_score") else 1.0998
comp_summary = load_model_comparison(selected_farm)
if not comp_summary.empty:
    matched = comp_summary[(comp_summary["model"] == model_key) & (comp_summary["strategy"] == strategy_key)]
    if not matched.empty:
        threshold_val = float(matched.iloc[0]["optimal_threshold"])

# Active Event Calculations
ev_row = event_scores_df[event_scores_df["independent_event_id"] == selected_event] if not event_scores_df.empty else pd.DataFrame()
if not ev_row.empty and strategy_key in ev_row.columns:
    ev_score = float(ev_row.iloc[0][strategy_key])
    ev_label = str(ev_row.iloc[0]["event_label"])
else:
    ev_score = 0.0
    ev_label = "normal"
    
score_margin = ev_score - threshold_val
is_abnormal = ev_score >= threshold_val

attr_df = load_attribution_matrix(model_key)
ev_attr = attr_df[attr_df["independent_event_id"] == selected_event] if not attr_df.empty else pd.DataFrame()
primary_comp = str(ev_attr.iloc[0]["primary_component"]) if not ev_attr.empty and "primary_component" in ev_attr.columns else "Generator_Bearing"
feat_rank_df = load_feature_ranking(model_key, selected_farm)

# Active System Badge in Sidebar Footer
st.sidebar.markdown(textwrap.dedent(f"""\
<div style="margin-top: 16px; padding: 10px; background-color: #1e293b; border-radius: 0px; font-size: 11px; color: #94a3b8;">
    <div style="font-weight: 700; color: #f8fafc; margin-bottom: 2px;">ACTIVE SYSTEM CONFIG</div>
    <div><b>Model:</b> {selected_model_name}</div>
    <div><b>Agg:</b> {selected_strategy_name}</div>
    <div><b>Threshold:</b> <code style="color: #38bdf8;">{threshold_val:.4f}</code></div>
</div>
"""), unsafe_allow_html=True)


# =============================================================================
# PAGE 1: OVERVIEW / OPERATIONAL MONITORING (Section 8 Order)
# =============================================================================
if selected_page == nav_overview:
    # 1. Quantitative KPI Summary Row (NO normal/abnormal badges inside KPI cards)
    render_fleet_kpis(n_turbines=5, n_events=21, det_rate=90.9, far_rate=30.0)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Dedicated Condition Status Panel (Below KPI row)
    render_condition_status_panel(selected_turbine, selected_event, ev_score, threshold_val, score_margin, primary_comp, is_abnormal)
    
    # 3. Anomaly Score + Threshold Visual Timeline
    fig_trend = plot_anomaly_trend(event_scores_df, strategy_key, threshold_val)
    st.plotly_chart(fig_trend, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 4. Component Contribution Bar Chart & Actual vs Expected Telemetry
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        comp_scores_all = load_component_scores(model_key, selected_farm)
        ev_comp = comp_scores_all[comp_scores_all["independent_event_id"] == selected_event] if not comp_scores_all.empty else pd.DataFrame()
        if not ev_comp.empty:
            score_col = "component_p95" if strategy_key == "event_p95_score" else "component_score"
            tot_sum = ev_comp[score_col].sum() if ev_comp[score_col].sum() > 0 else 1.0
            comp_display_df = pd.DataFrame({
                "component_group": ev_comp["component_group"],
                "contribution_score": ev_comp[score_col],
                "pct": (ev_comp[score_col] / tot_sum * 100.0)
            })
            fig_comp = plot_component_attribution_percentage(comp_display_df, primary_comp)
            st.plotly_chart(fig_comp, use_container_width=True)
            
    with col_c2:
        res_df = load_event_residuals(model_key, selected_event, selected_farm)
        if not res_df.empty:
            tgt_col = "target_name" if "target_name" in res_df.columns else "target_column"
            top_target = res_df[tgt_col].iloc[0] if tgt_col in res_df.columns else "dT_genbrg_nde"
            fig_act = plot_actual_vs_expected(res_df, top_target)
            st.plotly_chart(fig_act, use_container_width=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 5. Top Contributing Measurements (Human-Readable Descriptions First)
    feat_rank_df = load_feature_ranking(model_key, selected_farm)
    render_feature_contribution_table(feat_rank_df)
    
    # 6. Maintenance Inspection Guidance Directive
    top_feat_name = feat_rank_df.iloc[0]["target_column"] if not feat_rank_df.empty else "dT_genbrg_nde"
    render_maintenance_recommendation(primary_comp, top_feat_name)
    
    # 7. Technical Information Accordion
    with st.expander("🔬 Technical Model & Validation Details (NBM Residuals & Z-Scores)"):
        st.markdown(textwrap.dedent(f"""\
        - **Normal Behaviour Model (NBM):** `{selected_model_name}` trained on healthy SCADA operational baseline (`status_type_id = 0`).
        - **Validation Protocol:** 21 Independent Leave-One-Event-Out (LOEO) validation folds.
        - **Residual Standardisation:** Standardized Z-Score Z = (Y - Y_pred) / sigma_train.
        - **Calibrated LOEO Decision Threshold:** `{threshold_val:.4f}` (optimizes ROC-AUC / PR-AUC trade-off).
        - **Current Event Raw Anomaly Score:** `{ev_score:.4f}` (`{score_margin:+.4f}` margin).
        """))

# =============================================================================
# PAGE 2: LIVE MONITORING
# =============================================================================
elif selected_page == nav_live:
    render_condition_status_panel(selected_turbine, selected_event, ev_score, threshold_val, score_margin, primary_comp, is_abnormal)
    
    res_df = load_event_residuals(model_key, selected_event, selected_farm)
    if not res_df.empty:
        tgt_col = "target_name" if "target_name" in res_df.columns else "target_column"
        available_targets = sorted(res_df[tgt_col].unique())
        selected_target = st.selectbox("Select SCADA Telemetry Signal", options=available_targets, index=0)
        
        c1, c2 = st.columns(2)
        with c1:
            fig_act = plot_actual_vs_expected(res_df, selected_target)
            st.plotly_chart(fig_act, use_container_width=True)
        with c2:
            fig_z = plot_zscore_residuals(res_df, selected_target)
            st.plotly_chart(fig_z, use_container_width=True)
    else:
        st.info("Time-series telemetry residuals data unavailable for selected event.")

# =============================================================================
# PAGE 3: ANOMALY EVENTS (DEEP-DIVE INVESTIGATION)
# =============================================================================
elif selected_page == nav_anomaly:
    render_condition_status_panel(selected_turbine, selected_event, ev_score, threshold_val, score_margin, primary_comp, is_abnormal)
    
    st.markdown("### Event Physical Context & Ground-Truth Record")
    ev_desc_row = event_index_df[event_index_df["independent_event_id"] == selected_event] if not event_index_df.empty else pd.DataFrame()
    if not ev_desc_row.empty:
        r = ev_desc_row.iloc[0]
        st.markdown(textwrap.dedent(f"""\
        <div class="section-card">
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px;">
                <div>
                    <div style="font-size:11px; color:#64748b; font-weight:700;">TURBINE ASSET</div>
                    <div style="font-size:16px; font-weight:700; color:#0f172a;">{r.get('turbine_uid', selected_turbine)}</div>
                </div>
                <div>
                    <div style="font-size:11px; color:#64748b; font-weight:700;">GROUND-TRUTH LABEL</div>
                    <div style="font-size:16px; font-weight:700; color:#0f172a;">{r.get('event_label', 'anomaly')}</div>
                </div>
                <div>
                    <div style="font-size:11px; color:#64748b; font-weight:700;">HISTORICAL LOG</div>
                    <div style="font-size:14px; color:#334155;">{r.get('event_description', 'Thermal deviation event')}</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)
        
    feat_rank_df = load_feature_ranking(model_key, selected_farm)
    render_feature_contribution_table(feat_rank_df)
    
    top_feat_name = feat_rank_df.iloc[0]["target_column"] if not feat_rank_df.empty else "dT_genbrg_nde"
    render_maintenance_recommendation(primary_comp, top_feat_name)

# =============================================================================
# PAGE 4: COMPONENT ANALYSIS
# =============================================================================
elif selected_page == nav_comp:
    st.markdown(f"### Physical Subsystem Attribution: Turbine **{selected_turbine}** ({selected_event})")
    
    comp_scores_all = load_component_scores(model_key, selected_farm)
    ev_comp = comp_scores_all[comp_scores_all["independent_event_id"] == selected_event] if not comp_scores_all.empty else pd.DataFrame()
    
    if not ev_comp.empty:
        score_col = "component_p95" if strategy_key == "event_p95_score" else "component_score"
        tot_sum = ev_comp[score_col].sum() if ev_comp[score_col].sum() > 0 else 1.0
        
        comp_display_df = pd.DataFrame({
            "component_group": ev_comp["component_group"],
            "contribution_score": ev_comp[score_col],
            "pct": (ev_comp[score_col] / tot_sum * 100.0)
        })
        
        c1, c2 = st.columns([7, 3])
        with c1:
            fig_comp = plot_component_attribution_percentage(comp_display_df, primary_comp)
            st.plotly_chart(fig_comp, use_container_width=True)
        with c2:
            st.markdown(textwrap.dedent(f"""\
            <div style="background-color:#ffffff; border:1px solid #e5e7eb; border-left:4px solid #0284c7; padding:18px; border-radius:0px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase;">PRIMARY CONTRIBUTOR</div>
                <div style="font-size:20px; font-weight:800; color:#0f172a; margin:4px 0 8px 0;">{primary_comp.replace('_', ' ')}</div>
                <div style="font-size:13px; color:#334155;">Relative Share: <b style="color:#0284c7;">{(ev_comp[ev_comp['component_group']==primary_comp][score_col].values[0]/tot_sum*100.0 if not ev_comp[ev_comp['component_group']==primary_comp].empty else 0.0):.1f}%</b></div>
            </div>
            """), unsafe_allow_html=True)
            
    feat_rank_df = load_feature_ranking(model_key, selected_farm)
    render_feature_contribution_table(feat_rank_df)

# =============================================================================
# PAGE 5: MODEL PERFORMANCE (MODEL BENCHMARK)
# =============================================================================
elif selected_page == nav_model:
    st.markdown("### Official 12-Combination LOEO Cross-Validation Benchmark")
    st.markdown("<p style='font-size:13px; color:#64748b; margin-top:-6px;'>Out-of-fold performance evaluated across 21 independent leave-one-event-out validation folds.</p>", unsafe_allow_html=True)
    
    comp_df = load_model_comparison(selected_farm)
    if not comp_df.empty:
        df_bench = comp_df.copy()
        df_bench["det_rate"] = (df_bench["recall"] * 100.0).round(1)
        df_bench["far_rate"] = (df_bench["fpr"] * 100.0).round(1)
        df_bench["specificity"] = ((1.0 - df_bench["fpr"]) * 100.0).round(1)
        
        st.dataframe(
            df_bench[["model", "strategy", "det_rate", "far_rate", "specificity", "roc_auc", "pr_auc", "f1_max", "optimal_threshold"]].rename(columns={
                "model": "Model Family",
                "strategy": "Aggregation Strategy",
                "det_rate": "Detection Rate (Recall %)",
                "far_rate": "False Alarm Rate (FPR %)",
                "specificity": "Specificity (%)",
                "roc_auc": "ROC-AUC",
                "pr_auc": "PR-AUC",
                "f1_max": "Max F1 Score",
                "optimal_threshold": "Calibrated Threshold"
            }),
            use_container_width=True,
            height=400
        )
        
    st.markdown("<br>", unsafe_allow_html=True)
    fig_agg = plot_aggregation_comparison(comp_df)
    st.plotly_chart(fig_agg, use_container_width=True)

# =============================================================================
# PAGE 6: EVENT HISTORY
# =============================================================================
elif selected_page == nav_history:
    st.markdown("### Historical LOEO Event Log (21 Evaluated Events)")
    
    scores_df = load_event_scores(model_key, selected_farm)
    if not scores_df.empty and not event_index_df.empty:
        merged_events = event_index_df.merge(scores_df[["independent_event_id", strategy_key]], on="independent_event_id", how="left")
        merged_events["score"] = merged_events[strategy_key]
        merged_events["margin"] = merged_events["score"] - threshold_val
        merged_events["decision"] = merged_events["score"].map(lambda s: "Abnormal" if s >= threshold_val else "Normal")
        
        f1, f2 = st.columns(2)
        with f1:
            filter_t = st.selectbox("Filter by Turbine Asset", ["All"] + sorted(merged_events["turbine_uid"].unique().tolist()))
        with f2:
            filter_l = st.selectbox("Filter Ground-Truth Label", ["All", "anomaly", "normal"])
            
        df_show = merged_events.copy()
        if filter_t != "All": df_show = df_show[df_show["turbine_uid"] == filter_t]
        if filter_l != "All": df_show = df_show[df_show["event_label"] == filter_l]
        
        st.dataframe(
            df_show[["independent_event_id", "turbine_uid", "event_start", "event_end", "event_label", "event_description", "score", "margin", "decision"]].rename(columns={
                "independent_event_id": "Event ID",
                "turbine_uid": "Turbine Asset",
                "event_start": "Start Time",
                "event_end": "End Time",
                "event_label": "Ground Truth",
                "event_description": "Historical Description",
                "score": "Anomaly Score",
                "margin": "Score Margin",
                "decision": "System Decision"
            }),
            use_container_width=True,
            height=450
        )

# =============================================================================
# PAGE 7: HOW IT WORKS
# =============================================================================
elif selected_page == nav_how:
    st.markdown("### End-to-End Methodological Architecture")
    
    st.markdown(textwrap.dedent("""\
    <div style="background-color:#ffffff; border:1px solid #e5e7eb; border-radius:0px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.04); margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; gap:10px; text-align:center;">
            <div style="flex:1; background-color:#f8fafc; border:1px solid #e2e8f0; padding:10px; border-radius:0px;">
                <div style="font-size:11px; font-weight:700; color:#0284c7;">STEP 1</div>
                <div style="font-size:12px; font-weight:700; color:#0f172a; margin-top:2px;">SCADA TELEMETRY</div>
            </div>
            <div style="align-self:center; color:#94a3b8; font-weight:800;">→</div>
            <div style="flex:1; background-color:#f8fafc; border:1px solid #e2e8f0; padding:10px; border-radius:0px;">
                <div style="font-size:11px; font-weight:700; color:#0284c7;">STEP 2</div>
                <div style="font-size:12px; font-weight:700; color:#0f172a; margin-top:2px;">NBM MODEL</div>
            </div>
            <div style="align-self:center; color:#94a3b8; font-weight:800;">→</div>
            <div style="flex:1; background-color:#f8fafc; border:1px solid #e2e8f0; padding:10px; border-radius:0px;">
                <div style="font-size:11px; font-weight:700; color:#0284c7;">STEP 3</div>
                <div style="font-size:12px; font-weight:700; color:#0f172a; margin-top:2px;">Z-SCORE RESIDUALS</div>
            </div>
            <div style="align-self:center; color:#94a3b8; font-weight:800;">→</div>
            <div style="flex:1; background-color:#f8fafc; border:1px solid #e2e8f0; padding:10px; border-radius:0px;">
                <div style="font-size:11px; font-weight:700; color:#0284c7;">STEP 4</div>
                <div style="font-size:12px; font-weight:700; color:#0f172a; margin-top:2px;">P95 AGGREGATION</div>
            </div>
            <div style="align-self:center; color:#94a3b8; font-weight:800;">→</div>
            <div style="flex:1; background-color:#f8fafc; border:1px solid #e2e8f0; padding:10px; border-radius:0px;">
                <div style="font-size:11px; font-weight:700; color:#dc2626;">STEP 5</div>
                <div style="font-size:12px; font-weight:700; color:#0f172a; margin-top:2px;">ATTRIBUTION & SOP</div>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)

# =============================================================================
# PAGE 8: MAINTENANCE GUIDE
# =============================================================================
elif selected_page == nav_maint:
    st.markdown("### Field Maintenance & Inspection Guide")
    render_condition_status_panel(selected_turbine, selected_event, ev_score, threshold_val, score_margin, primary_comp, is_abnormal)
    
    feat_rank_df = load_feature_ranking(model_key, selected_farm)
    top_feat_name = feat_rank_df.iloc[0]["target_column"] if not feat_rank_df.empty else "dT_genbrg_nde"
    render_maintenance_recommendation(primary_comp, top_feat_name)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Subsystem SCADA Telemetry & Residual Deviations")
    render_feature_contribution_table(feat_rank_df)

# =============================================================================
# PAGE 9: SYSTEM CONFIGURATION
# =============================================================================
elif selected_page == nav_system:
    st.markdown("### Data Manifest & Pipeline Configuration")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(textwrap.dedent("""\
        <div class="kpi-card-unified">
            <div class="kpi-card-label">DATASET</div>
            <div class="kpi-card-value">Wind Farm A</div>
            <div class="kpi-card-sub">425,023 SCADA Rows</div>
        </div>
        """), unsafe_allow_html=True)
    with c2:
        st.markdown(textwrap.dedent("""\
        <div class="kpi-card-unified">
            <div class="kpi-card-label">LOEO FOLDS</div>
            <div class="kpi-card-value">21 Folds</div>
            <div class="kpi-card-sub">11 Anomaly / 10 Control Folds</div>
        </div>
        """), unsafe_allow_html=True)
    with c3:
        st.markdown(textwrap.dedent("""\
        <div class="kpi-card-unified">
            <div class="kpi-card-label">CONDITIONING</div>
            <div class="kpi-card-value">8 Features</div>
            <div class="kpi-card-sub">Wind, Power, Bins</div>
        </div>
        """), unsafe_allow_html=True)
    with c4:
        st.markdown(textwrap.dedent("""\
        <div class="kpi-card-unified">
            <div class="kpi-card-label">TARGET SIGNALS</div>
            <div class="kpi-card-value">21 Signals</div>
            <div class="kpi-card-sub">7 Component Groups</div>
        </div>
        """), unsafe_allow_html=True)

