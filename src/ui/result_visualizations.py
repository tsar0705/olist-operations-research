"""Phase 2.9 — maps and result visualizations.

All geographic coordinates come from the validated Phase 1 canonical bundle.
This module contains presentation helpers only; it does not calculate
optimization decisions, transportation costs, or geography.
"""
from __future__ import annotations

import math
import pandas as pd


def _coords(bundle) -> pd.DataFrame:
    required = {"state", "latitude", "longitude"}
    coords = bundle.state_coordinates.copy()
    missing = required - set(coords.columns)
    if missing:
        raise ValueError(f"Canonical state coordinates missing columns: {sorted(missing)}")
    return coords.set_index("state")[["latitude", "longitude"]]


def _money(v) -> str:
    try:
        return f"R$ {float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _st():
    import streamlit as st
    return st


def _safe_plotly():
    try:
        import plotly.graph_objects as go
        import plotly.express as px
        return go, px
    except ImportError:
        return None, None


def _base_geo(fig, fitbounds="locations"):
    fig.update_geos(
        scope="south america",
        showcountries=True,
        showland=True,
        showocean=True,
        showlakes=True,
        coastlinecolor="rgba(80,80,80,0.45)",
        countrycolor="rgba(80,80,80,0.55)",
        fitbounds=fitbounds,
        lataxis_range=[-35, 6],
        lonaxis_range=[-75, -30],
    )
    fig.update_layout(
        height=620,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
    )
    return fig


def _flow_width(orders: float, max_orders: float) -> float:
    if max_orders <= 0:
        return 1.0
    # sqrt scaling keeps a few large lanes from visually swallowing the map.
    return max(0.8, min(7.0, 0.8 + 5.5 * math.sqrt(float(orders) / max_orders)))


def render_demand_map(bundle, *, key_prefix="demand"):
    """Show all customer states sized by canonical demand."""
    st = _st()
    go, px = _safe_plotly()
    if go is None:
        st.info("Install Plotly to display the geographic visualization.")
        return

    demand = bundle.demand_table.copy()
    coords = _coords(bundle)
    demand = demand[demand["state"].isin(coords.index)].copy()
    if demand.empty:
        st.info("No demand states with valid canonical coordinates.")
        return

    demand = demand.merge(
        coords.reset_index(),
        on="state",
        how="left",
        validate="one_to_one",
    )
    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lat=demand["latitude"],
        lon=demand["longitude"],
        mode="markers+text",
        text=demand["state"],
        textposition="top center",
        marker=dict(
            size=(demand["demand_orders"].clip(lower=1).pow(0.5) / 5.0).clip(6, 28),
            opacity=0.78,
        ),
        customdata=demand[["demand_orders", "demand_share_pct"]].to_numpy(),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Demand: %{customdata[0]:,.0f} orders<br>"
            "Share: %{customdata[1]:.2f}%<extra></extra>"
        ),
        name="Customer demand",
    ))
    _base_geo(fig)
    st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_map")


def render_model1_network_map(
    bundle,
    result,
    *,
    max_flows: int = 60,
    key_prefix="model1_network",
):
    st = _st()
    """Render Model 1 hubs, demand nodes, and largest shipment lanes."""
    go, _ = _safe_plotly()
    if go is None:
        st.info("Install Plotly to display the shipment-flow map.")
        return

    flows = result.flow_table
    if flows is None or flows.empty:
        st.info("No positive shipment flows to display.")
        return

    coords = _coords(bundle)
    flows = flows.copy()
    valid = flows[
        flows["origin_hub"].isin(coords.index)
        & flows["destination_state"].isin(coords.index)
    ].copy()
    if valid.empty:
        st.info("Shipment flows do not overlap the canonical coordinate table.")
        return

    valid = valid.sort_values("orders_shipped", ascending=False)
    shown = valid.head(max_flows)
    max_orders = float(shown["orders_shipped"].max())

    fig = go.Figure()

    # Shipment lanes first.
    for row in shown.itertuples(index=False):
        o = coords.loc[row.origin_hub]
        d = coords.loc[row.destination_state]
        fig.add_trace(go.Scattergeo(
            lat=[o.latitude, d.latitude],
            lon=[o.longitude, d.longitude],
            mode="lines",
            line=dict(width=_flow_width(row.orders_shipped, max_orders)),
            opacity=0.42,
            showlegend=False,
            customdata=[[row.origin_hub, row.destination_state,
                         float(row.orders_shipped), float(row.cost_per_order)]],
            hovertemplate=(
                "%{customdata[0]} → %{customdata[1]}<br>"
                "Orders: %{customdata[2]:,.0f}<br>"
                "Cost/order: R$ %{customdata[3]:,.2f}<extra></extra>"
            ),
        ))

    # Open hubs.
    decision = result.decision_table.copy()
    if {"state", "open"}.issubset(decision.columns):
        hubs = decision[decision["open"] & decision["state"].isin(coords.index)].copy()
    else:
        hub_states = result.metadata.get("opened_hubs", [])
        hubs = pd.DataFrame({"state": [s for s in hub_states if s in coords.index]})

    if not hubs.empty:
        hc = coords.loc[hubs["state"].tolist()]
        fig.add_trace(go.Scattergeo(
            lat=hc["latitude"],
            lon=hc["longitude"],
            text=hc.index,
            mode="markers+text",
            textposition="top center",
            marker=dict(size=14, symbol="diamond"),
            name="Opened hubs",
            hovertemplate="<b>%{text}</b><br>Opened facility<extra></extra>",
        ))

    # Demand nodes for context.
    demand = bundle.demand_table[
        bundle.demand_table["state"].isin(coords.index)
    ].copy()
    dc = coords.loc[demand["state"].tolist()]
    fig.add_trace(go.Scattergeo(
        lat=dc["latitude"],
        lon=dc["longitude"],
        text=demand["state"],
        mode="markers",
        marker=dict(size=6, opacity=0.65),
        customdata=demand[["demand_orders"]].to_numpy(),
        name="Demand states",
        hovertemplate="<b>%{text}</b><br>Demand: %{customdata[0]:,.0f} orders<extra></extra>",
    ))

    _base_geo(fig)
    st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_map")
    if len(valid) > len(shown):
        st.caption(
            f"Map shows the top {len(shown)} shipment lanes by order volume; "
            f"the full {len(valid)}-lane solution remains available in the table."
        )


def render_model2_assignment_map(
    bundle,
    result,
    *,
    key_prefix="model2_assignment",
):
    st = _st()
    """Render Model 2 seller-state → customer-state assignments."""
    go, _ = _safe_plotly()
    if go is None:
        st.info("Install Plotly to display the assignment map.")
        return

    assignments = result.decision_table
    if assignments is None or assignments.empty:
        st.info("No assignments to display.")
        return

    coords = _coords(bundle)
    valid = assignments[
        assignments["assigned_seller_state"].isin(coords.index)
        & assignments["customer_state"].isin(coords.index)
    ].copy()
    if valid.empty:
        st.info("Assignments do not overlap the canonical coordinate table.")
        return

    max_orders = float(valid["demand_orders"].max())
    fig = go.Figure()

    for row in valid.itertuples(index=False):
        o = coords.loc[row.assigned_seller_state]
        d = coords.loc[row.customer_state]
        fig.add_trace(go.Scattergeo(
            lat=[o.latitude, d.latitude],
            lon=[o.longitude, d.longitude],
            mode="lines",
            line=dict(width=_flow_width(row.demand_orders, max_orders)),
            opacity=0.42,
            showlegend=False,
            customdata=[[
                row.assigned_seller_state,
                row.customer_state,
                float(row.demand_orders),
                float(row.cost_per_order),
            ]],
            hovertemplate=(
                "%{customdata[0]} → %{customdata[1]}<br>"
                "Orders: %{customdata[2]:,.0f}<br>"
                "Cost/order: R$ %{customdata[3]:,.2f}<extra></extra>"
            ),
        ))

    seller_states = [
        s for s in result.metadata.get("seller_states_used", [])
        if s in coords.index
    ]
    if seller_states:
        sc = coords.loc[seller_states]
        fig.add_trace(go.Scattergeo(
            lat=sc["latitude"],
            lon=sc["longitude"],
            text=sc.index,
            mode="markers+text",
            textposition="top center",
            marker=dict(size=14, symbol="diamond"),
            name="Used seller states",
            hovertemplate="<b>%{text}</b><br>Seller state<extra></extra>",
        ))

    customer_states = valid["customer_state"].drop_duplicates().tolist()
    cc = coords.loc[customer_states]
    fig.add_trace(go.Scattergeo(
        lat=cc["latitude"],
        lon=cc["longitude"],
        text=cc.index,
        mode="markers",
        marker=dict(size=6, opacity=0.65),
        name="Customer states",
        hovertemplate="<b>%{text}</b><br>Assigned customer state<extra></extra>",
    ))

    _base_geo(fig)
    st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_map")


def render_model1_result_visuals(bundle, result):
    """Full Model 1 result-visualization section."""
    st = _st()
    st.subheader("Network map")
    render_model1_network_map(bundle, result)

    st.subheader("Hub utilization")
    util = result.utilization_table.copy()
    if util is not None and not util.empty:
        util = util.sort_values("utilization_pct", ascending=False)
        st.bar_chart(util.set_index("state")["utilization_pct"])
        st.caption("Utilization is scenario-scaled orders served divided by scenario-scaled hub capacity.")

    if result.flow_table is not None and not result.flow_table.empty:
        st.subheader("Shipment-cost profile")
        flows = result.flow_table.copy()
        flows["lane_cost"] = flows["orders_shipped"] * flows["cost_per_order"]
        top = flows.sort_values("lane_cost", ascending=False).head(15)
        top["lane"] = top["origin_hub"] + " → " + top["destination_state"]
        st.bar_chart(top.set_index("lane")["lane_cost"])
        st.caption("Top 15 shipment lanes ranked by total lane transportation cost.")

    if result.metadata.get("shadow_prices"):
        shadow = pd.DataFrame(result.metadata["shadow_prices"])
        if not shadow.empty and {"region", "shadow_price"}.issubset(shadow.columns):
            st.subheader("Demand-state marginal cost")
            shadow = shadow.sort_values("shadow_price", ascending=False)
            st.bar_chart(shadow.set_index("region")["shadow_price"])
            st.caption("Model 1 dual/shadow-price diagnostic for one additional order of demand.")


def render_model2_result_visuals(bundle, result):
    """Full Model 2 result-visualization section."""
    st = _st()
    st.subheader("Assignment map")
    render_model2_assignment_map(bundle, result)

    st.subheader("Seller-state utilization")
    util = result.utilization_table.copy()
    if util is not None and not util.empty:
        util = util.sort_values("utilization_pct", ascending=False)
        st.bar_chart(util.set_index("state")["utilization_pct"])
        st.caption("Utilization is assigned demand divided by scenario-scaled seller-state capacity.")

    assignments = result.decision_table.copy()
    if assignments is not None and not assignments.empty:
        st.subheader("Assignment cost profile")
        assignments["assignment_cost"] = assignments["demand_orders"] * assignments["cost_per_order"]
        top = assignments.sort_values("assignment_cost", ascending=False).head(15)
        top["lane"] = top["assigned_seller_state"] + " → " + top["customer_state"]
        st.bar_chart(top.set_index("lane")["assignment_cost"])
        st.caption("Top 15 single-source assignments ranked by transportation cost.")

        st.subheader("Assignment-distance/cost table")
        display = top[[
            "lane", "demand_orders", "cost_per_order", "assignment_cost"
        ]].rename(columns={
            "lane": "Lane",
            "demand_orders": "Orders",
            "cost_per_order": "Cost/order",
            "assignment_cost": "Total lane cost",
        })
        st.dataframe(display, width="stretch", hide_index=True)


def render_result_downloads(result, prefix: str):
    """Consistent CSV exports for visualized result tables."""
    st = _st()
    if result.decision_table is not None:
        st.download_button(
            "Download decision table",
            result.decision_table.to_csv(index=False).encode("utf-8"),
            f"{prefix}_decision_table.csv",
            "text/csv",
            key=f"{prefix}_decision_download",
        )
    if result.utilization_table is not None:
        st.download_button(
            "Download utilization table",
            result.utilization_table.to_csv(index=False).encode("utf-8"),
            f"{prefix}_utilization.csv",
            "text/csv",
            key=f"{prefix}_util_download",
        )
    if result.flow_table is not None:
        st.download_button(
            "Download flow table",
            result.flow_table.to_csv(index=False).encode("utf-8"),
            f"{prefix}_flows.csv",
            "text/csv",
            key=f"{prefix}_flow_download",
        )
