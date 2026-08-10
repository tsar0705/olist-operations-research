"""Release-readiness page used by the final dashboard."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from ..config import DEFAULT_CONFIG
from ..release import release_ready, run_release_checks
from .theme import section_intro


def render_release_status_page() -> None:
    section_intro(
        "Release & Architecture Status",
        "Phase 2.12 — final UI polish, deployment diagnostics, and release hardening.",
    )

    root = Path(__file__).resolve().parents[2]
    checks = run_release_checks(root)
    ready = release_ready(checks)

    if ready:
        st.success("RELEASE READY — required runtime and project checks passed.")
    else:
        st.warning(
            "RELEASE BLOCKED — the dashboard can explain the missing pieces, but it should not be presented as a fully runnable release."
        )

    passed = sum(check.passed for check in checks)
    st.metric("Release checks", f"{passed}/{len(checks)} passed")

    rows = [
        {"Check": check.name, "Status": "PASS" if check.passed else "BLOCKED", "Detail": check.detail}
        for check in checks
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    st.subheader("Release rules")
    st.markdown(
        """
- Real Olist data only; no synthetic/demo fallback.
- Optimization is blocked until the canonical dataset is valid.
- Only validation-passed optimal results are displayed as accepted recommendations.
- Scenario parameters are explicit assumptions, not hidden model constants.
- Geographic visualizations consume Phase 1 coordinates.
- Downloads are generated from validated result objects.
- The entry-point `app.py` remains a thin orchestration layer.
        """
    )

    st.caption(f"Dashboard version: {DEFAULT_CONFIG.version}")
