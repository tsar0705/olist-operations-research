"""Small presentation helpers used by the release-hardened dashboard."""
from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        [data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.18);
            border-radius: 12px;
            padding: .75rem 1rem;
        }
        .phase-card {
            border: 1px solid rgba(128,128,128,.18);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            margin-bottom: .75rem;
            background: rgba(128,128,128,.035);
        }
        .status-pill {
            display: inline-block;
            border-radius: 999px;
            padding: .2rem .65rem;
            font-size: .82rem;
            font-weight: 600;
            border: 1px solid rgba(128,128,128,.2);
        }
        footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_intro(title: str, description: str) -> None:
    st.title(title)
    st.caption(description)


def status_card(label: str, state: str, detail: str = "") -> None:
    if state == "ready":
        st.success(f"✓ {label}: ready")
    elif state == "blocked":
        st.error(f"✕ {label}: blocked")
    else:
        st.warning(f"• {label}: {state}")
    if detail:
        st.caption(detail)
