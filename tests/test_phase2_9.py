import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app_state import AppState, get_app_state
from src.ui.result_visualizations import _flow_width


def test_app_state_exposes_canonical_bundle_alias():
    state = AppState()
    assert state.canonical_bundle is None
    assert state.dataset_fingerprint is None


def test_flow_width_is_bounded_and_monotone():
    values = [_flow_width(v, 100000) for v in [1, 100, 1000, 10000, 100000]]
    assert values == sorted(values)
    assert values[0] >= 0.8
    assert values[-1] <= 7.0


def test_visualization_coordinate_contract_has_no_ui_constants():
    source = (ROOT / "src" / "ui" / "result_visualizations.py").read_text()
    assert "STATE_COORDS" not in source
    assert 'state_coordinates' in source
