"""Release/environment diagnostics for the Phase 2.12 dashboard.

This module deliberately performs checks without importing the full analytical
pipeline.  That lets the dashboard explain a broken deployment instead of
crashing during module import.
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReleaseCheck:
    name: str
    passed: bool
    detail: str
    severity: str = "error"


REQUIRED_MODULES = (
    "streamlit",
    "pandas",
    "numpy",
    "scipy",
    "plotly",
)

REQUIRED_PROJECT_FILES = (
    "src/config.py",
    "src/app_state.py",
    "src/data/phase1_service.py",
    "src/data/upload_validation.py",
    "src/optimization/scenarios.py",
    "src/optimization/cache.py",
    "src/optimization/model1_cflp.py",
    "src/optimization/model2_assignment.py",
    "src/optimization/services.py",
    "src/validation/data_checks.py",
    "src/analytics/sensitivity.py",
    "phase1_outputs/PHASE_1_4_CALIBRATION.json",
)


def run_release_checks(root: str | Path) -> list[ReleaseCheck]:
    root = Path(root)
    checks: list[ReleaseCheck] = []

    for module in REQUIRED_MODULES:
        installed = importlib.util.find_spec(module) is not None
        checks.append(
            ReleaseCheck(
                name=f"dependency:{module}",
                passed=installed,
                detail="installed" if installed else "not installed",
            )
        )

    for relative in REQUIRED_PROJECT_FILES:
        path = root / relative
        exists = path.is_file()
        checks.append(
            ReleaseCheck(
                name=f"project:{relative}",
                passed=exists,
                detail="present" if exists else "missing from release tree",
            )
        )

    # Source-level architectural guard: the application entry point must not
    # contain the prototype solver/geography implementation.
    app = root / "app.py"
    if app.is_file():
        source = app.read_text(encoding="utf-8")
        forbidden = ("STATE_COORDS", "LpProblem", "LpVariable", "haversine", "build_demo_demand")
        bad = [token for token in forbidden if token in source]
        checks.append(
            ReleaseCheck(
                name="architecture:thin-app",
                passed=not bad,
                detail="presentation/orchestration only" if not bad else f"forbidden tokens: {', '.join(bad)}",
            )
        )

    return checks


def release_ready(checks: list[ReleaseCheck]) -> bool:
    return all(check.passed for check in checks if check.severity == "error")
