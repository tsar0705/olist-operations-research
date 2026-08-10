from dataclasses import dataclass, field
from typing import Any

@dataclass
class AppState:
    """Transient state container; Streamlit session_state owns its lifetime."""
    raw_data: dict[str, Any] = field(default_factory=dict)
    canonical_data: Any = None
    validation_report: Any = None
    order_fact: Any = None
    state_coordinates: Any = None
    distance_matrix: Any = None
    demand_table: Any = None
    seller_capacity: Any = None
    candidate_hubs: Any = None
    cost_matrix: Any = None
    model1_result: Any = None
    model2_result: Any = None
    sensitivity_results: Any = None

    @property
    def canonical_bundle(self):
        """Phase 2.6–2.9 compatibility alias for the canonical dataset."""
        return self.canonical_data

    @property
    def dataset_fingerprint(self):
        bundle = self.canonical_data
        return getattr(bundle, "dataset_fingerprint", None)

    @property
    def metadata(self):
        bundle = self.canonical_data
        if bundle is None:
            return {}
        return getattr(bundle, "metadata", {})

    @property
    def optimization_cache(self):
        # Backward-compatible transient cache namespace for UI pages.
        if not hasattr(self, "_optimization_cache"):
            self._optimization_cache = {}
        return self._optimization_cache


def get_app_state(st_module):
    """Return the single AppState stored in Streamlit session state."""
    if "app_state" not in st_module.session_state:
        st_module.session_state.app_state = AppState()
    return st_module.session_state.app_state

