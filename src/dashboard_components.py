"""
Dashboard Components Module (src/dashboard_components.py)
=========================================================
Enterprise Industrial AI Design System for WINDGUARD AI.
Unified design system: #F6F8FA background, white cards, thin #E5E7EB borders,
subtle shadows, clean typography, dedicated status panels, and Plotly charts.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import textwrap

def inject_custom_css():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

    /* -------------------------------------------------------------------------
       1. GLOBAL APP CANVAS & TYPOGRAPHY SYSTEM (Inter Sans / Inter)
       ------------------------------------------------------------------------- */
    html, body, [data-testid="stAppViewContainer"], .stApp,
    input, select, textarea, p, label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* Preserve Material Symbols icon font for all icon elements */
    [data-testid="stIconMaterial"],
    .material-symbols-rounded,
    [data-testid*="stIcon"] {
        font-family: 'Material Symbols Rounded' !important;
        font-weight: normal !important;
        font-style: normal !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        display: inline-flex !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-smoothing: antialiased !important;
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background-color: #f6f8fa !important;
        color: #0f172a !important;
    }
    
    /* -------------------------------------------------------------------------
       2. RESTORE TOP-RIGHT 3-DOT MENU (#MainMenu / stToolbar)
       ------------------------------------------------------------------------- */
    header[data-testid="stHeader"], [data-testid="stHeader"], .stAppHeader {
        display: flex !important;
        visibility: visible !important;
        background: transparent !important;
        height: 2.75rem !important;
        min-height: 2.75rem !important;
        justify-content: flex-end !important;
        align-items: center !important;
        padding: 0 1.5rem !important;
        z-index: 999 !important;
        pointer-events: auto !important;
    }

    /* Hide ONLY the deploy button, KEEP the 3-dot menu visible & fully functional */
    .stDeployButton, [data-testid="stDeployButton"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
    }

    #MainMenu, [data-testid="stToolbar"] {
        display: flex !important;
        visibility: visible !important;
        pointer-events: auto !important;
    }

    #MainMenu button, [data-testid="stToolbar"] button {
        color: #475569 !important;
        border-radius: 0px !important;
    }

    #MainMenu button:hover, [data-testid="stToolbar"] button:hover {
        color: #0f172a !important;
        background-color: #e2e8f0 !important;
    }

    /* Center Content Container & Top Padding so 3-dot menu never overlaps */
    .block-container {
        max-width: 1400px !important;
        padding-top: 3.25rem !important;
        padding-bottom: 3rem !important;
    }

    /* -------------------------------------------------------------------------
       3. ENTERPRISE SIDEBAR & DEDICATED COLLAPSE CONTROL
       ------------------------------------------------------------------------- */
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b !important;
        color: #f8fafc !important;
    }

    [data-testid="stSidebar"][aria-expanded="true"] {
        min-width: 260px !important;
        max-width: 260px !important;
        width: 260px !important;
    }

    /* Dedicated top position for collapse button in normal flow — NEVER overlaps brand */
    [data-testid="stSidebarHeader"] {
        display: flex !important;
        justify-content: flex-end !important;
        align-items: center !important;
        height: 38px !important;
        min-height: 38px !important;
        padding: 6px 12px 0 12px !important;
        margin: 0 !important;
        background: transparent !important;
        position: relative !important;
        font-size: 0 !important;
        color: transparent !important;
        overflow: hidden !important;
    }

    /* Dedicated top position for collapse button in normal flow — NEVER overlaps brand */
    [data-testid="stSidebarHeader"] {
        display: flex !important;
        justify-content: flex-end !important;
        align-items: center !important;
        height: 38px !important;
        min-height: 38px !important;
        padding: 6px 12px 0 12px !important;
        margin: 0 !important;
        background: transparent !important;
        position: relative !important;
        font-size: 0 !important;
        color: transparent !important;
        overflow: hidden !important;
    }

    /* Suppress any raw ligature or fallback text (like 'keyboard_double_arrow_left' -> 'key') */
    [data-testid="stSidebarHeader"] button,
    [data-testid="stSidebarCollapseButton"],
    button[data-testid="stBaseButton-header"],
    button[kind="header"] {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 28px !important;
        height: 28px !important;
        min-width: 28px !important;
        min-height: 28px !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid #1e293b !important;
        cursor: pointer !important;
        border-radius: 4px !important;
        position: relative !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        font-size: 0 !important;
        color: transparent !important;
        text-indent: -9999px !important;
    }

    /* Hide ALL internal child elements (spans, divs, text, SVGs) so 'key' can never appear */
    [data-testid="stSidebarHeader"] button *,
    [data-testid="stSidebarCollapseButton"] *,
    button[data-testid="stBaseButton-header"] *,
    button[kind="header"] * {
        display: none !important;
        visibility: hidden !important;
        font-size: 0 !important;
        color: transparent !important;
        width: 0 !important;
        height: 0 !important;
    }

    [data-testid="stSidebarCollapseButton"]::after,
    button[data-testid="stBaseButton-header"]::after,
    [data-testid="stSidebarHeader"] button::after {
        content: '«' !important;
        text-indent: 0 !important;
        font-size: 16px !important;
        line-height: 1 !important;
        font-weight: 700 !important;
        color: #94a3b8 !important;
        position: absolute !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        visibility: visible !important;
        display: block !important;
    }

    [data-testid="stSidebarCollapseButton"]:hover, 
    button[data-testid="stBaseButton-header"]:hover,
    [data-testid="stSidebarHeader"] button:hover {
        background: rgba(255, 255, 255, 0.12) !important;
        border-color: #38bdf8 !important;
    }

    [data-testid="stSidebarCollapseButton"]:hover::after,
    button[data-testid="stBaseButton-header"]:hover::after,
    [data-testid="stSidebarHeader"] button:hover::after {
        color: #38bdf8 !important;
    }

    /* Sidebar Content directly below the dedicated header bar in normal flow */
    [data-testid="stSidebarUserContent"], 
    [data-testid="stSidebarContent"] {
        padding: 4px 12px 24px 12px !important;
        margin-top: 0 !important;
    }

    /* Expand button when sidebar is collapsed (>>) */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        visibility: visible !important;
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 1000 !important;
    }

    [data-testid="stSidebarCollapsedControl"] * {
        font-size: 0 !important;
        color: transparent !important;
        visibility: hidden !important;
    }

    [data-testid="stSidebarCollapsedControl"] button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 32px !important;
        height: 32px !important;
        background: #0f172a !important;
        color: transparent !important;
        border-radius: 4px !important;
        border: 1px solid #1e293b !important;
        position: relative !important;
        cursor: pointer !important;
    }

    [data-testid="stSidebarCollapsedControl"] button::after {
        content: '»' !important;
        font-size: 18px !important;
        line-height: 1 !important;
        font-weight: 700 !important;
        color: #38bdf8 !important;
        position: absolute !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        visibility: visible !important;
    }

    [data-testid="stSidebarCollapsedControl"] button:hover {
        background: #1e293b !important;
        border-color: #38bdf8 !important;
    }

    /* Scope text colors specifically to user content to avoid polluting headers */
    [data-testid="stSidebarUserContent"] p,
    [data-testid="stSidebarUserContent"] span,
    [data-testid="stSidebarUserContent"] label,
    [data-testid="stSidebarUserContent"] div {
        color: #f8fafc !important;
    }

    /* Sidebar Section Headers */
    .sidebar-section-header {
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #64748b !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        margin: 12px 0 6px 0 !important;
        padding-bottom: 4px !important;
        border-bottom: 1px solid #1e293b !important;
    }

    /* -------------------------------------------------------------------------
       4. SIDEBAR NAVIGATION BUTTONS — EXACT ICON ALIGNMENT & FIXED ICON COLUMN
       ------------------------------------------------------------------------- */
    [data-testid="stSidebar"] .stButton,
    [data-testid="stSidebar"] div.stButton {
        width: 100% !important;
        margin: 0 0 3px 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
    }

    /* All rows have the EXACT same left padding (14px) and height (40px) */
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"],
    [data-testid="stSidebar"] button:not([data-testid="stBaseButton-header"]):not([data-testid="stSidebarCollapseButton"]) {
        width: 100% !important;
        min-height: 40px !important;
        height: 40px !important;
        padding: 0 14px !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-start !important;
        text-align: left !important;
        border-radius: 0px !important;
        border: none !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        line-height: 1 !important;
        transition: all 0.15s ease-in-out !important;
        box-shadow: none !important;
        cursor: pointer !important;
        box-sizing: border-box !important;
        gap: 0 !important;
    }

    /* Inactive Navigation Item: 100% Transparent Background, Clean Visible Slate Text (#CBD5E1) */
    [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] .stButton > button[kind="secondary"],
    [data-testid="stSidebar"] .stButton > button:not([kind="primary"]),
    [data-testid="stSidebar"] button:not([kind="primary"]):not([data-testid="stBaseButton-header"]):not([data-testid="stSidebarCollapseButton"]) {
        background-color: transparent !important;
        background: transparent !important;
        color: #cbd5e1 !important;
        border: 1px solid transparent !important;
        border-radius: 0px !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover,
    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover,
    [data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover,
    [data-testid="stSidebar"] button:not([kind="primary"]):not([data-testid="stBaseButton-header"]):not([data-testid="stSidebarCollapseButton"]):hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
        background: rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        border-color: transparent !important;
        border-radius: 0px !important;
    }

    /* Active Navigation Item: Solid Blue #0284C7 Full Rectangular Row Fill */
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"],
    [data-testid="stSidebar"] .stButton > button[kind="primary"],
    [data-testid="stSidebar"] button[kind="primary"] {
        background-color: #0284c7 !important;
        background: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: 1px solid #0284c7 !important;
        border-radius: 0px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2) !important;
    }

    /* Horizontal flex container inside button with zero intermediate gap */
    [data-testid="stSidebar"] .stButton > button > div,
    [data-testid="stSidebar"] button:not([data-testid="stBaseButton-header"]) > div {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-start !important;
        text-align: left !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        gap: 0 !important;
    }

    /* FIXED-WIDTH ICON COLUMN: Exactly 22px wide x 22px high, vertically centered, starting at 14px padding */
    [data-testid="stSidebar"] .stButton > button::before {
        content: '' !important;
        display: inline-block !important;
        width: 22px !important;
        min-width: 22px !important;
        max-width: 22px !important;
        height: 22px !important;
        min-height: 22px !important;
        max-height: 22px !important;
        margin: 0 !important;
        margin-right: 12px !important; /* EXACT FIXED 12px SPACING TO TEXT */
        padding: 0 !important;
        flex-shrink: 0 !important;
        background-color: currentColor !important;
        -webkit-mask-repeat: no-repeat !important;
        mask-repeat: no-repeat !important;
        -webkit-mask-position: center !important;
        mask-position: center !important;
        -webkit-mask-size: 21px 21px !important;
        mask-size: 21px 21px !important;
        box-sizing: border-box !important;
        vertical-align: middle !important;
    }

    /* Vector SVG Icons for each navigation item */
    /* 0. Overview */
    div.st-key-nav_btn_0 button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M3 3h8v8H3V3zm10 0h8v8h-8V3zM3 13h8v8H3v-8zm10 0h8v8h-8v-8z'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M3 3h8v8H3V3zm10 0h8v8h-8V3zM3 13h8v8H3v-8zm10 0h8v8h-8v-8z'/%3E%3C/svg%3E") !important;
    }

    /* 1. Live Monitoring */
    div.st-key-nav_btn_1 button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M13 2L3 14h8l-1 8 11-12h-8l1-8z'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M13 2L3 14h8l-1 8 11-12h-8l1-8z'/%3E%3C/svg%3E") !important;
    }

    /* 2. Anomaly Events */
    div.st-key-nav_btn_2 button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M12 2L1 21h22L12 2zm0 3.5L20 19H4L12 5.5zM11 10v4h2v-4h-2zm0 6v2h2v-2h-2z'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M12 2L1 21h22L12 2zm0 3.5L20 19H4L12 5.5zM11 10v4h2v-4h-2zm0 6v2h2v-2h-2z'/%3E%3C/svg%3E") !important;
    }

    /* 3. Component Analysis */
    div.st-key-nav_btn_3 button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z'/%3E%3C/svg%3E") !important;
    }

    /* 4. Model Performance */
    div.st-key-nav_btn_4 button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M5 9.2h3V19H5V9.2zM10.6 5h2.8v14h-2.8V5zm5.6 8H19v6h-2.8v-6zM3 21h18v2H3v-2z'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M5 9.2h3V19H5V9.2zM10.6 5h2.8v14h-2.8V5zm5.6 8H19v6h-2.8v-6zM3 21h18v2H3v-2z'/%3E%3C/svg%3E") !important;
    }

    /* 5. Event History */
    div.st-key-nav_btn_5 button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6a7 7 0 1 1 2.05 4.95l-1.42 1.42A8.96 8.96 0 0 0 13 21a9 9 0 1 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6a7 7 0 1 1 2.05 4.95l-1.42 1.42A8.96 8.96 0 0 0 13 21a9 9 0 1 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z'/%3E%3C/svg%3E") !important;
    }

    /* 6. How It Works */
    div.st-key-nav_btn_6 button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z'/%3E%3C/svg%3E") !important;
    }

    /* 7. Maintenance Guide */
    div.st-key-nav_btn_7 button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.6C.5 7 .9 10 2.9 12c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.3z'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.6C.5 7 .9 10 2.9 12c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.3z'/%3E%3C/svg%3E") !important;
    }

    /* 8. System Configuration */
    div.st-key-nav_btn_8 button::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.48.48 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z'/%3E%3C/svg%3E") !important;
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.48.48 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z'/%3E%3C/svg%3E") !important;
    }

    /* Paragraph and Label inside Button */
    [data-testid="stSidebar"] .stButton > button p,
    [data-testid="stSidebar"] button:not([data-testid="stBaseButton-header"]) p,
    [data-testid="stSidebar"] .stButton > button span,
    [data-testid="stSidebar"] button:not([data-testid="stBaseButton-header"]) span {
        color: inherit !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 13.5px !important;
        font-weight: inherit !important;
        text-align: left !important;
        justify-content: flex-start !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1 !important;
        display: inline-block !important;
        white-space: nowrap !important;
    }

    /* Suppress any unwanted list markers or bullets */
    [data-testid="stSidebar"] ul, 
    [data-testid="stSidebar"] ol, 
    [data-testid="stSidebar"] li {
        list-style: none !important;
        list-style-type: none !important;
        padding-left: 0 !important;
        margin-left: 0 !important;
    }

    /* -------------------------------------------------------------------------
       5. UNIFIED ENTERPRISE RECTANGULAR BOX / CARD SYSTEM — 100% SHARP EDGES
       ------------------------------------------------------------------------- */
    .main {
        background-color: #f6f8fa !important;
        color: #0f172a !important;
    }

    /* Unified Control Selectboxes — SHARP EDGES & SOLID BLACK BORDER OUTLINE */
    [data-testid="stSelectbox"] div[data-baseweb="select"],
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [role="combobox"],
    [data-testid="stSelectbox"] div[aria-haspopup="listbox"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1.5px solid #000000 !important;
        border-radius: 0px !important;
        box-shadow: none !important;
        outline: none !important;
    }

    [data-testid="stSelectbox"] div[data-baseweb="select"]:hover,
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
    [data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within,
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within {
        border-color: #000000 !important;
        border: 1.5px solid #000000 !important;
        box-shadow: none !important;
    }

    [data-testid="stSelectbox"] span, [data-testid="stSelectbox"] div, [data-testid="stSelectbox"] p {
        color: #0f172a !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }

    [data-testid="stSelectbox"] svg {
        fill: #000000 !important;
        color: #000000 !important;
    }

    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    div[data-baseweb="menu"],
    div[data-baseweb="menu"] > ul {
        border-radius: 0px !important;
        border: 1.5px solid #000000 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }

    div[data-baseweb="popover"] ul li, div[data-baseweb="menu"] ul li {
        color: #0f172a !important;
        background-color: #ffffff !important;
        font-size: 13px !important;
        border-radius: 0px !important;
    }

    /* Universal Rectangular Card Styling — ALL SHARP EDGES (border-radius: 0px) */
    .kpi-card-unified {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 0px !important;
        padding: 16px 20px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
        height: 100%;
    }
    .kpi-card-label {
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #64748b !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 4px !important;
    }
    .kpi-card-value {
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        line-height: 1.1 !important;
        letter-spacing: -0.03em !important;
    }
    .kpi-card-sub {
        font-size: 11.5px !important;
        font-weight: 500 !important;
        color: #94a3b8 !important;
        margin-top: 4px !important;
    }

    /* Condition Status Panel — Rectangular, Sharp Edges */
    .status-panel-abnormal {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 6px solid #dc2626 !important;
        border-radius: 0px !important;
        padding: 18px 22px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }
    .status-panel-normal {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 6px solid #16a34a !important;
        border-radius: 0px !important;
        padding: 18px 22px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }

    /* Badges — Sharp Edges */
    .badge-abnormal {
        background-color: #fee2e2 !important;
        color: #991b1b !important;
        border: 1px solid #fca5a5 !important;
        padding: 3px 10px !important;
        border-radius: 0px !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        letter-spacing: 0.04em !important;
    }
    .badge-normal {
        background-color: #dcfce7 !important;
        color: #166534 !important;
        border: 1px solid #86efac !important;
        padding: 3px 10px !important;
        border-radius: 0px !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        letter-spacing: 0.04em !important;
    }

    /* Section Cards — Sharp Edges */
    .section-card {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 0px !important;
        padding: 18px 22px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }

    /* Container border styling — Sharp Edges */
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        border-color: #cbd5e1 !important;
        border-radius: 0px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }

    /* Global Sharp Edges Enforcement for all rectangular boxes and buttons */
    *, *::before, *::after,
    [data-testid="stAppViewContainer"] button,
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSelectbox"] *,
    [data-testid="stDataFrame"],
    [data-testid="stExpander"],
    details {
        border-radius: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)

def render_top_navbar(page_name="Operational Overview"):
    """Compact Top Header Navigation Bar with clean typography and rectangular edges."""
    st.markdown(textwrap.dedent(f"""\
    <div style="display:flex; justify-content:space-between; align-items:center; background-color:#ffffff; border:1px solid #cbd5e1; border-radius:0px; padding:12px 20px; margin-bottom:16px; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
        <div>
            <div style="font-size:18px; font-weight:800; color:#0f172a; margin:0; letter-spacing:-0.02em;">Turbine Condition Monitoring</div>
            <div style="font-size:12px; font-weight:600; color:#64748b; margin-top:2px;">
                Wind Farm A &nbsp;<span style="color:#cbd5e1;">│</span>&nbsp; 
                <span style="color:#0284c7; font-weight:700;">{page_name}</span>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <div style="text-align:right;">
                <div style="font-size:11px; color:#64748b; font-weight:500;">Last Telemetry Sync: 10:42 AM</div>
                <div style="font-size:12px; font-weight:700; color:#15803d; display:flex; align-items:center; justify-content:flex-end; gap:6px; margin-top:1px;">
                    <span style="color:#16a34a; font-size:9px;">●</span> System Operational
                </div>
            </div>
            <div style="background-color:#0284c7; color:#ffffff; width:34px; height:34px; border-radius:0px; font-weight:700; font-size:12px; display:flex; align-items:center; justify-content:center;">
                OP
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)

def render_fleet_kpis(n_turbines=5, n_events=21, det_rate=90.9, far_rate=30.0):
    """Quantitative KPI Cards Row (NO normal/abnormal status inside KPI cards)."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(textwrap.dedent(f"""\
        <div class="kpi-card-unified">
            <div class="kpi-card-label">TURBINES MONITORED</div>
            <div class="kpi-card-value">{n_turbines}</div>
            <div class="kpi-card-sub">Wind Farm A Fleet Assets</div>
        </div>
        """), unsafe_allow_html=True)
    with c2:
        st.markdown(textwrap.dedent(f"""\
        <div class="kpi-card-unified">
            <div class="kpi-card-label">LOEO FOLDS EVALUATED</div>
            <div class="kpi-card-value">{n_events}</div>
            <div class="kpi-card-sub">11 Anomaly / 10 Control Folds</div>
        </div>
        """), unsafe_allow_html=True)
    with c3:
        st.markdown(textwrap.dedent(f"""\
        <div class="kpi-card-unified">
            <div class="kpi-card-label">DETECTION RATE</div>
            <div class="kpi-card-value" style="color:#0284c7;">{det_rate:.1f}%</div>
            <div class="kpi-card-sub">Sensitivity (Recall)</div>
        </div>
        """), unsafe_allow_html=True)
    with c4:
        st.markdown(textwrap.dedent(f"""\
        <div class="kpi-card-unified">
            <div class="kpi-card-label">FALSE ALARM RATE</div>
            <div class="kpi-card-value" style="color:#d97706;">{far_rate:.1f}%</div>
            <div class="kpi-card-sub">False Positive Rate (FPR)</div>
        </div>
        """), unsafe_allow_html=True)

def render_top_filter_bar(model_map, strategy_map, load_event_scores_fn):
    """Contained, Unified Filter Toolbar Container."""
    with st.container(border=True):
        st.markdown("<div style='font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px;'>MONITORING CONTROLS</div>", unsafe_allow_html=True)
        f1, f2, f3, f4, f5 = st.columns([2.6, 2.2, 2.0, 1.6, 1.6])
        with f1:
            selected_farm = st.selectbox(
                "Wind Farm Site",
                options=["Wind Farm A (21 LOEO Events)", "Wind Farm B (Fleet B Monitoring)"],
                index=0
            )
        with f2:
            selected_model_name = st.selectbox(
                "Normal Behaviour Model",
                options=list(model_map.keys()),
                index=0
            )
            model_key = model_map[selected_model_name]
            
        with f3:
            selected_strategy_name = st.selectbox(
                "Aggregation Strategy",
                options=list(strategy_map.keys()),
                index=0
            )
            strategy_key = strategy_map[selected_strategy_name]
            
        event_scores_df = load_event_scores_fn(model_key, selected_farm)
        available_turbines = sorted(event_scores_df["turbine_uid"].unique()) if not event_scores_df.empty else ["A0", "A10", "A11", "A13", "A21"]
        
        with f4:
            selected_turbine = st.selectbox("Turbine Asset", options=available_turbines, index=0)
            
        turbine_events = event_scores_df[event_scores_df["turbine_uid"] == selected_turbine]["independent_event_id"].unique() if not event_scores_df.empty else ["E40"]
        
        with f5:
            selected_event = st.selectbox("Event Window", options=turbine_events, index=0)
            
    return selected_farm, model_key, selected_model_name, strategy_key, selected_strategy_name, selected_turbine, selected_event, event_scores_df

def render_condition_status_panel(turbine, event_id, score, threshold, margin, primary_comp, is_abnormal):
    """Dedicated Condition Status Panel with Anomaly Score vs Threshold Gauge Bar."""
    panel_class = "status-panel-abnormal" if is_abnormal else "status-panel-normal"
    status_title = "● ABNORMAL BEHAVIOUR DETECTED" if is_abnormal else "● NORMAL OPERATING BEHAVIOUR"
    status_desc = (
        "The event anomaly score exceeds the calibrated decision threshold."
        if is_abnormal else
        "The event anomaly score remains within the normal operating envelope."
    )
    margin_color = "#dc2626" if margin >= 0 else "#16a34a"
    margin_str = f"+{margin:.4f} above limit" if margin >= 0 else f"{margin:.4f} below limit"
    badge_class = "badge-abnormal" if is_abnormal else "badge-normal"
    badge_text = "ABNORMAL" if is_abnormal else "NORMAL"
    clean_comp_name = primary_comp.replace('_', ' ') if primary_comp else "Generator Bearing"
    
    # Progress gauge percentage for score vs threshold limit
    max_val = max(score, threshold * 1.5, 2.0)
    score_pct = min(max((score / max_val) * 100.0, 5.0), 100.0)
    thresh_pct = min(max((threshold / max_val) * 100.0, 5.0), 100.0)
    bar_color = "#dc2626" if is_abnormal else "#16a34a"

    # Single contiguous HTML string without blank lines or leading space indentation
    html_content = (
        f'<div class="{panel_class}">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid #f1f5f9; padding-bottom:8px;">'
        f'<div><div style="margin:0; color:#0f172a; font-size:16px; font-weight:800;">{status_title}</div>'
        f'<div style="margin:2px 0 0 0; font-size:12px; color:#64748b;">{status_desc}</div></div>'
        f'<div><span class="{badge_class}">{badge_text}</span></div></div>'
        f'<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:16px; margin-bottom:12px;">'
        f'<div><div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase;">TURBINE & EVENT</div>'
        f'<div style="font-size:18px; font-weight:800; color:#0f172a;">Turbine {turbine} &nbsp;│&nbsp; {event_id}</div></div>'
        f'<div><div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase;">ANOMALY SCORE</div>'
        f'<div style="font-size:18px; font-weight:800; color:#0f172a;">{score:.4f}</div></div>'
        f'<div><div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase;">NORMAL LIMIT (THRESHOLD)</div>'
        f'<div style="font-size:18px; font-weight:800; color:#0f172a;">{threshold:.4f}</div></div>'
        f'<div><div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase;">PRIMARY SUBSYSTEM</div>'
        f'<div style="font-size:16px; font-weight:800; color:#0284c7;">{clean_comp_name}</div></div></div>'
        f'<div style="margin-top:8px; background-color:#f8fafc; border:1px solid #e2e8f0; border-radius:0px; padding:10px 14px;">'
        f'<div style="display:flex; justify-content:space-between; font-size:11px; font-weight:700; color:#64748b; margin-bottom:4px;">'
        f'<span>NORMAL RANGE (0.000)</span><span>CALIBRATED THRESHOLD LIMIT ({threshold:.4f})</span>'
        f'<span style="color:{margin_color}; font-weight:800;">SCORE: {score:.4f} ({margin_str})</span></div>'
        f'<div style="position:relative; width:100%; height:10px; background-color:#e2e8f0; border-radius:0px; overflow:hidden;">'
        f'<div style="width:{score_pct:.1f}%; height:100%; background-color:{bar_color}; border-radius:0px; transition: width 0.3s ease;"></div>'
        f'<div style="position:absolute; left:{thresh_pct:.1f}%; top:0; bottom:0; width:3px; background-color:#0f172a; box-shadow:0 0 4px rgba(0,0,0,0.5);"></div>'
        f'</div></div></div>'
    )
    
    st.markdown(html_content, unsafe_allow_html=True)

def plot_component_attribution_percentage(comp_df, primary_comp):
    """Clean Horizontal Bar Chart: Main Contributing Components."""
    if comp_df.empty:
        return go.Figure()
        
    df_sorted = comp_df.sort_values("pct", ascending=True).copy()
    
    # Handle missing / invalid scores cleanly (no NaN/None/undefined)
    df_sorted["pct"] = df_sorted["pct"].fillna(0.0)
    df_sorted["contribution_score"] = df_sorted["contribution_score"].fillna(0.0)
    
    name_map = {
        "Generator_Bearing": "Generator Bearing",
        "Generator_Electrical": "Generator Electrical",
        "Gearbox": "Gearbox",
        "Hydraulic": "Hydraulic System",
        "Mechanical": "Mechanical Drive",
        "Power": "Power Output",
        "Transformer": "Transformer Winding"
    }
    df_sorted["display_name"] = df_sorted["component_group"].map(lambda x: name_map.get(x, str(x).replace("_", " ")))
    # Neutral slate color for all bars, highlighted red for top contributor
    colors = ['#dc2626' if raw_c == primary_comp else '#64748b' for raw_c in df_sorted["component_group"]]
    
    fig = go.Figure(go.Bar(
        x=df_sorted["pct"],
        y=df_sorted["display_name"],
        orientation='h',
        marker=dict(color=colors, line=dict(color='#ffffff', width=1)),
        text=[f"{pct:.1f}% (|Z| = {score:.2f}σ)" for pct, score in zip(df_sorted["pct"], df_sorted["contribution_score"])],
        textposition='outside',
        textfont=dict(color="#0f172a", size=11, family="sans-serif")
    ))
    
    fig.update_layout(
        title=dict(
            text="<b>Main Contributing Components</b><br><span style='font-size:12px; font-weight:400; color:#64748b;'>Relative contribution of component-level deviations</span>",
            font=dict(size=14, color="#0f172a")
        ),
        xaxis=dict(title="Relative Contribution Percentage (%)", gridcolor="#f1f5f9", tickfont=dict(color="#64748b", size=11), range=[0, 105]),
        yaxis=dict(title="", tickfont=dict(size=12, color="#0f172a", weight="bold")),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=80, t=55, b=30),
        height=300
    )
    return fig

def plot_actual_vs_expected(res_df, target_col):
    """Actual vs Expected Behaviour Line Chart."""
    tgt_col = "target_name" if "target_name" in res_df.columns else "target_column"
    sub = res_df[res_df[tgt_col] == target_col].sort_values("time_stamp").copy()
    if sub.empty:
        return go.Figure()
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["time_stamp"], y=sub["actual_value"],
        mode='lines', name='Actual',
        line=dict(color='#0f172a', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=sub["time_stamp"], y=sub["predicted_value"],
        mode='lines', name='Expected',
        line=dict(color='#0284c7', width=2, dash='dash')
    ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>Actual vs Expected Behaviour: {target_col}</b><br><span style='font-size:12px; font-weight:400; color:#64748b;'>Observed component behaviour compared with modelled normal operating behaviour</span>",
            font=dict(size=14, color="#0f172a")
        ),
        xaxis=dict(title="Timestamp", gridcolor="#f1f5f9", tickfont=dict(color="#64748b")),
        yaxis=dict(title="Signal Unit", gridcolor="#f1f5f9", tickfont=dict(color="#64748b")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=55, b=30),
        height=300
    )
    return fig

def plot_zscore_residuals(res_df, target_col):
    """Standardized Z-Score Residual Line Chart."""
    tgt_col = "target_name" if "target_name" in res_df.columns else "target_column"
    sub = res_df[res_df[tgt_col] == target_col].sort_values("time_stamp").copy()
    if sub.empty:
        return go.Figure()
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["time_stamp"], y=sub["z_score"],
        mode='lines', name='Residual (Z)',
        line=dict(color='#dc2626', width=1.6)
    ))
    
    fig.add_hline(y=2.5, line_dash="dash", line_color="#d97706", annotation_text="Diagnostic Limit (+2.5σ)", annotation_position="top right", annotation_font_color="#d97706")
    fig.add_hline(y=-2.5, line_dash="dash", line_color="#d97706")
    
    fig.update_layout(
        title=dict(
            text=f"<b>Standardized Residual (Z-Score): {target_col}</b><br><span style='font-size:12px; font-weight:400; color:#64748b;'>Normalized standard deviation excursion from baseline</span>",
            font=dict(size=14, color="#0f172a")
        ),
        xaxis=dict(title="Timestamp", gridcolor="#f1f5f9", tickfont=dict(color="#64748b")),
        yaxis=dict(title="Standard Deviations (σ)", gridcolor="#f1f5f9", tickfont=dict(color="#64748b")),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=55, b=30),
        height=300
    )
    return fig

def plot_anomaly_trend(scores_df, strategy_key="event_p95_score", threshold=1.0998):
    """Event Anomaly Score Timeline Chart."""
    if scores_df.empty:
        return go.Figure()
        
    df = scores_df.sort_values("independent_event_id").copy()
    df["score"] = df[strategy_key]
    colors = ['#dc2626' if label == 'anomaly' else '#16a34a' for label in df["event_label"]]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["independent_event_id"],
        y=df["score"],
        mode='lines+markers',
        marker=dict(size=8, color=colors, line=dict(color='#ffffff', width=1.5)),
        line=dict(color='#94a3b8', width=1.5, dash='dot'),
        text=[f"Event: {e}<br>Turbine: {t}<br>Score: {s:.4f}<br>Label: {l}" for e, t, s, l in zip(df["independent_event_id"], df["turbine_uid"], df["score"], df["event_label"])],
        hoverinfo='text'
    ))
    
    fig.add_hline(y=threshold, line_dash="dash", line_color="#dc2626", annotation_text=f"Decision Threshold ({threshold:.4f})", annotation_position="top left")
    
    fig.update_layout(
        title=dict(text="<b>21 LOEO Event Anomaly Score Timeline</b>", font=dict(size=14, color="#0f172a")),
        xaxis=dict(title="Independent LOEO Event ID", gridcolor="#f1f5f9", tickfont=dict(color="#64748b")),
        yaxis=dict(title="Anomaly Score", gridcolor="#f1f5f9", tickfont=dict(color="#64748b")),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=40, b=30),
        height=300
    )
    return fig

def plot_aggregation_comparison(comp_df):
    """Aggregation Strategy Bar Chart."""
    if comp_df.empty:
        return go.Figure()
        
    df = comp_df.copy()
    df["det_rate"] = df["recall"] * 100.0
    df["far_rate"] = df["fpr"] * 100.0
    
    strat_names = {
        "event_p95_score": "95th Percentile (P95)",
        "persistence_score": "Persistence Score",
        "event_median_score": "Event Median"
    }
    df["strat_display"] = df["strategy"].map(lambda x: strat_names.get(x, x))
    ridge_df = df[df["model"] == "ridge"].copy()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ridge_df["strat_display"], y=ridge_df["det_rate"],
        name="Detection Rate (Recall %)", marker_color="#0284c7"
    ))
    fig.add_trace(go.Bar(
        x=ridge_df["strat_display"], y=ridge_df["far_rate"],
        name="False Alarm Rate (FPR %)", marker_color="#d97706"
    ))
    
    fig.update_layout(
        title=dict(text="<b>Aggregation Strategy Benchmark Comparison (Ridge NBM)</b>", font=dict(size=14, color="#0f172a")),
        barmode='group',
        xaxis=dict(title="Strategy", gridcolor="#f1f5f9", tickfont=dict(color="#64748b")),
        yaxis=dict(title="Percentage (%)", gridcolor="#f1f5f9", tickfont=dict(color="#64748b"), range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=40, b=30),
        height=300
    )
    return fig

def render_feature_contribution_table(feat_rank_df):
    """Human-Readable SCADA Measurements Associated with Deviation (Section 11)."""
    st.markdown("### Measurements Associated With the Deviation")
    st.markdown("<p style='font-size:12px; color:#64748b; margin-top:-6px; margin-bottom:12px;'>SCADA sensors exhibiting highest residual deviation during the event window</p>", unsafe_allow_html=True)
    
    if feat_rank_df.empty:
        st.info("Insufficient data")
        return
        
    name_descriptions = {
        "dT_genbrg_de": "Generator Bearing Temperature — Drive End",
        "dT_genbrg_nde": "Generator Bearing Temperature — Non-Drive End",
        "dT_stator_phase1": "Stator Temperature Difference — Phase 1",
        "dT_stator_phase2": "Stator Temperature Difference — Phase 2",
        "dT_stator_phase3": "Stator Temperature Difference — Phase 3",
        "dT_gearbox_oil": "Main Gearbox Sump Oil Temperature Difference",
        "dT_gearbox_brg": "Gearbox Bearing Temperature Difference",
        "dT_trafo_phase1": "Transformer Temperature Difference — Phase 1",
        "dT_trafo_phase2": "Transformer Temperature Difference — Phase 2",
        "dT_trafo_phase3": "Transformer Temperature Difference — Phase 3",
        "dT_hyd_oil": "Hydraulic Pitch Unit Oil Temperature Difference"
    }
    
    df_show = feat_rank_df.head(7).copy()
    # Clean NaN / None handling
    df_show["target_column"] = df_show["target_column"].fillna("dT_sensor")
    df_show["mean_abs_residual"] = df_show["mean_abs_residual"].fillna(0.0)
    df_show["pct_contribution"] = df_show["pct_contribution"].fillna(0.0)

    df_show["Measurement Description"] = df_show["target_column"].map(lambda x: name_descriptions.get(x, str(x).replace("_", " ").title()))
    df_show["Technical SCADA Name"] = df_show["target_column"]
    df_show["Mean Residual |Y - Y_pred|"] = df_show["mean_abs_residual"].round(4)
    df_show["Relative Contribution %"] = df_show["pct_contribution"].map(lambda x: f"{x:.1f}%")
    
    st.dataframe(
        df_show[["Measurement Description", "Technical SCADA Name", "Mean Residual |Y - Y_pred|", "Relative Contribution %"]],
        use_container_width=True
    )

def render_maintenance_recommendation(primary_comp, top_feature="dT_sensor"):
    """Technician-Facing Maintenance Inspection Guidance Card."""
    guide_map = {
        "Generator_Bearing": (
            "Generator Bearing Assembly Inspection",
            ["Inspect drive-end (DE) and non-drive-end (NDE) bearing temperatures.",
             "Check bearing grease lubrication levels and particle contamination.",
             "Perform high-frequency vibration analysis on generator bearing housing.",
             "Inspect cooling fan airflow and heat exchanger clearance."]
        ),
        "Generator_Electrical": (
            "Generator Stator & Winding Inspection",
            ["Inspect stator phase temperature sensors and delta-T spread.",
             "Verify rotor slip ring and brush gear condition for sparking or wear.",
             "Conduct insulation resistance (Megger) and winding balance tests.",
             "Examine stator cooling intake and exhaust ducting."]
        ),
        "Gearbox": (
            "Gearbox Lubrication & Mechanical Inspection",
            ["Inspect main gearbox bearing temperatures and oil sump temperature.",
             "Check oil filter differential pressure and inline particle counter.",
             "Collect gearbox oil sample for spectrographic wear debris analysis.",
             "Check gearbox mechanical sound and planetary stage vibration."]
        ),
        "Hydraulic": (
            "Hydraulic Pitch & Brake Unit Inspection",
            ["Inspect hydraulic oil reservoir temperature and fluid level.",
             "Verify hydraulic pump pressure and accumulator pre-charge.",
             "Inspect proportional valves and pitch cylinder seals for leaks.",
             "Check hydraulic oil cooler fan operation."]
        ),
        "Transformer": (
            "Main Transformer & Switchgear Inspection",
            ["Inspect transformer winding and core temperatures.",
             "Verify low-voltage and high-voltage bushing connections.",
             "Inspect transformer cooling radiators and oil circulation pumps.",
             "Perform dissolved gas analysis (DGA) on transformer oil."]
        )
    }
    
    clean_comp = primary_comp if primary_comp and str(primary_comp) != 'nan' else "Generator_Bearing"
    title, steps = guide_map.get(clean_comp, (
        f"{str(clean_comp).replace('_', ' ')} Subsystem Inspection",
        [f"Inspect SCADA measurement signal {top_feature} for thermal or electrical deviation.",
         "Verify sensor wiring and junction box connections.",
         "Conduct physical visual inspection of the subsystem assembly."]
    ))
    
    st.markdown(textwrap.dedent(f"""\
    <div style="background-color:#ffffff; border:1px solid #e5e7eb; border-left:5px solid #0284c7; border-radius:0px; padding:18px 22px; margin-top:16px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <h4 style="margin:0 0 6px 0; color:#0f172a; font-size:15px; font-weight:800;">📋 MAINTENANCE DIRECTIVE: {title}</h4>
        <p style="font-size:12px; color:#64748b; margin-bottom:10px;">
            <b>Primary Subsystem:</b> <code>{str(clean_comp).replace('_', ' ')}</code> &nbsp;│&nbsp; 
            <b>Target Signal:</b> <code>{top_feature}</code>
        </p>
        <div style="font-size:12px; font-weight:700; color:#0f172a; margin-bottom:4px;">FIELD INSPECTION CHECKLIST:</div>
        <ul style="margin:0 0 10px 0; padding-left:18px; font-size:13px; color:#334155;">
            {''.join([f'<li style="margin-bottom:3px;">{step}</li>' for step in steps])}
        </ul>
        <p style="font-size:11px; color:#94a3b8; margin:0;">
            <i>Note: Decision-support guidance for field technicians. Follow site safety, LOTO, and maintenance procedures.</i>
        </p>
    </div>
    """), unsafe_allow_html=True)
