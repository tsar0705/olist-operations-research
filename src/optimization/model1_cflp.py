"""
Model 1 — Capacitated Facility Location + Transportation.

Inputs are produced by Phase 1.1–1.4:
- optimization_demand_table.csv
- model1_candidate_hubs.csv
- transportation_cost_matrix_per_order.csv

Solver: SciPy MILP / HiGHS.

No data cleaning occurs here. No synthetic demand/cost data is generated.
Facility fixed cost remains an explicit scenario parameter because Olist
does not contain warehouse operating-cost observations.
"""

from pathlib import Path
import math
import numpy as np
import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

def solve_cflp(demand, hubs, cost_matrix, capacity_multiplier=1.2,
               fixed_cost=50_000, max_hubs=None):
    hub_states = hubs["state"].tolist()
    demand_states = demand["state"].tolist()

    D = demand.set_index("state")["demand_orders"].to_dict()
    base_cap = hubs.set_index("state")["base_capacity_orders"].to_dict()

    C = np.array([
        [float(cost_matrix.loc[cost_matrix["origin_state"] == h].iloc[0][d])
         for d in demand_states]
        for h in hub_states
    ])

    n_i, n_j = len(hub_states), len(demand_states)
    n = n_i + n_i*n_j
    caps = np.array(
        [math.ceil(base_cap[s] * capacity_multiplier)
         for s in hub_states], dtype=float
    )
    dem = np.array([D[s] for s in demand_states], dtype=float)

    objective = np.zeros(n)
    objective[:n_i] = fixed_cost
    objective[n_i:] = C.ravel()

    integrality = np.zeros(n, dtype=int)
    integrality[:n_i] = 1

    lower = np.zeros(n)
    upper = np.full(n, np.inf)
    upper[:n_i] = 1

    rows = n_i + n_j + (1 if max_hubs is not None else 0)
    A = lil_matrix((rows, n))
    lb = np.full(rows, -np.inf)
    ub = np.full(rows, np.inf)

    r = 0
    for j in range(n_j):
        for i in range(n_i):
            A[r, n_i + i*n_j + j] = 1
        lb[r] = ub[r] = dem[j]
        r += 1

    for i in range(n_i):
        A[r, i] = -caps[i]
        for j in range(n_j):
            A[r, n_i + i*n_j + j] = 1
        ub[r] = 0
        r += 1

    if max_hubs is not None:
        A[r, :n_i] = 1
        ub[r] = max_hubs

    result = milp(
        c=objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=LinearConstraint(A.tocsr(), lb, ub),
    )

    return result
