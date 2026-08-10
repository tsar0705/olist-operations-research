from __future__ import annotations
import pandas as pd

def validate_canonical_inputs(demand_table: pd.DataFrame, candidate_hubs: pd.DataFrame, cost_matrix: pd.DataFrame) -> dict[str, bool]:
    checks = {
        'demand_has_required_columns': {'state','demand_orders'}.issubset(demand_table.columns),
        'demand_states_unique': demand_table['state'].is_unique if 'state' in demand_table else False,
        'demand_nonnegative': bool((demand_table['demand_orders'] >= 0).all()) if 'demand_orders' in demand_table else False,
        'hub_has_required_columns': {'state','base_capacity_orders'}.issubset(candidate_hubs.columns),
        'hub_states_unique': candidate_hubs['state'].is_unique if 'state' in candidate_hubs else False,
        'hub_capacity_nonnegative': bool((candidate_hubs['base_capacity_orders'] >= 0).all()) if 'base_capacity_orders' in candidate_hubs else False,
        'cost_has_origin_state': 'origin_state' in cost_matrix.columns,
        'cost_rows_match_hubs': set(cost_matrix['origin_state']) == set(candidate_hubs['state']) if 'origin_state' in cost_matrix and 'state' in candidate_hubs else False,
        'cost_columns_cover_demand': set(demand_table['state']).issubset(set(cost_matrix.columns)) if 'state' in demand_table else False,
    }
    return checks
