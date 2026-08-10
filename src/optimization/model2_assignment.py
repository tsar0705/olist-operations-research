"""
Model 2 — Capacitated Single-Source Seller-State Assignment.

Inputs:
- optimization_demand_table.csv
- model1_candidate_hubs.csv
- transportation_cost_matrix_per_order.csv

z_ij = 1 when seller state i serves all demand in customer state j.

Objective:
    min Σ c_ij * D_j * z_ij

Constraints:
    Σ_i z_ij = 1
    Σ_j D_j z_ij <= Cap_i
    z_ij binary
"""

import math
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

def solve_assignment(demand, hubs, cost_matrix, capacity_multiplier=1.2):
    supply_states = hubs["state"].tolist()
    demand_states = demand["state"].tolist()
    D = demand.set_index("state")["demand_orders"].to_dict()
    base_cap = hubs.set_index("state")["base_capacity_orders"].to_dict()

    C = np.array([
        [float(cost_matrix.loc[cost_matrix["origin_state"] == i].iloc[0][j])
         for j in demand_states]
        for i in supply_states
    ])

    n_i, n_j = len(supply_states), len(demand_states)
    n = n_i*n_j
    caps = np.array(
        [math.ceil(base_cap[s]*capacity_multiplier) for s in supply_states],
        dtype=float
    )
    dem = np.array([D[s] for s in demand_states], dtype=float)

    objective = (C * dem[np.newaxis, :]).ravel()

    A = lil_matrix((n_j+n_i, n))
    lb = np.full(n_j+n_i, -np.inf)
    ub = np.full(n_j+n_i, np.inf)

    r = 0
    for j in range(n_j):
        for i in range(n_i):
            A[r, i*n_j+j] = 1
        lb[r] = ub[r] = 1
        r += 1

    for i in range(n_i):
        for j in range(n_j):
            A[r, i*n_j+j] = dem[j]
        ub[r] = caps[i]
        r += 1

    return milp(
        c=objective,
        integrality=np.ones(n, dtype=int),
        bounds=Bounds(np.zeros(n), np.ones(n)),
        constraints=LinearConstraint(A.tocsr(), lb, ub),
    )
