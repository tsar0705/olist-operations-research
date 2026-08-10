"""Optimization service boundary with validated structured results."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .model1_cflp import solve_cflp
from .model2_assignment import solve_assignment
from .scenarios import Scenario
from .result_models import OptimizationResult, ValidationResult


def _scaled_demand(demand, multiplier):
    out=demand.copy(); out['demand_orders']=out['demand_orders'].astype(float)*multiplier; return out

def _scaled_costs(cost_matrix, multiplier):
    out=cost_matrix.copy(); cols=[c for c in out.columns if c!='origin_state']; out[cols]=out[cols].astype(float)*multiplier; return out

def _require_valid_bundle(bundle):
    if not bundle.is_valid:
        refs={k:v for k,v in bundle.reference_checks.items() if v!=0}
        canon={k:v for k,v in bundle.canonical_checks.items() if not v}
        raise ValueError(f'Canonical Phase 1 data failed validation. reference={refs}; canonical={canon}')

def _solver_status(raw):
    return 'Optimal' if bool(getattr(raw,'success',False)) else str(getattr(raw,'message',getattr(raw,'status','Solver failure')))

def _model1_result(raw, demand, hubs, costs, scenario):
    hub_states=hubs['state'].tolist(); demand_states=demand['state'].tolist(); ni=len(hub_states); nj=len(demand_states)
    if not raw.success:
        return OptimizationResult('model1', _solver_status(raw), None, ValidationResult(False, {'solver_success':False}, [str(raw.message)]), metadata={'scenario':scenario.to_dict()}, raw_solver_result=raw)
    x=np.asarray(raw.x); y=x[:ni]; flows=x[ni:].reshape(ni,nj)
    D=demand.set_index('state')['demand_orders'].to_dict(); cap=hubs.set_index('state')['base_capacity_orders'].to_dict()
    cost_lookup={(r.origin_state, d):float(r[d]) for _,r in costs.iterrows() for d in demand_states}
    decision=[]; flow_rows=[]
    for i,h in enumerate(hub_states):
        shipped=float(flows[i].sum()); opened=bool(y[i] > .5)
        decision.append({'state':h,'open':opened,'capacity_orders':float(np.ceil(cap[h]*scenario.capacity_multiplier)),'orders_shipped':shipped})
        for j,d in enumerate(demand_states):
            q=float(flows[i,j])
            if q>1e-9: flow_rows.append({'origin_hub':h,'destination_state':d,'orders_shipped':q,'cost_per_order':cost_lookup[(h,d)],'transport_cost':q*cost_lookup[(h,d)]})
    decision_df=pd.DataFrame(decision); flow_df=pd.DataFrame(flow_rows)
    if flow_df.empty: flow_df=pd.DataFrame(columns=['origin_hub','destination_state','orders_shipped','cost_per_order','transport_cost'])
    util=decision_df.copy(); util['utilization_pct']=np.where(util.capacity_orders>0,100*util.orders_shipped/util.capacity_orders,0); util['used']=util['open']
    fixed=float(scenario.fixed_cost_per_hub*sum(y>.5)); transport=float(flow_df.transport_cost.sum()); reconstructed=fixed+transport
    checks={
      'solver_success':True,
      'demand_satisfied':bool(np.allclose(flows.sum(axis=0), [D[d] for d in demand_states], atol=1e-5)),
      'hub_capacity_respected':bool(np.all(flows.sum(axis=1) <= np.array([np.ceil(cap[h]*scenario.capacity_multiplier) for h in hub_states])+1e-5)),
      'closed_hubs_have_zero_flow':bool(np.all(flows[y<=.5] <= 1e-5)),
      'max_hubs_respected':scenario.max_hubs is None or int((y>.5).sum()) <= scenario.max_hubs,
      'nonnegative_flows':bool((flows>=-1e-9).all()),
      'objective_reconciles':abs(float(raw.fun)-reconstructed)<1e-4,
    }
    return OptimizationResult('model1','Optimal',float(raw.fun),ValidationResult(all(checks.values()),checks,[]),fixed_cost=fixed,transport_cost=transport,decision_table=decision_df,utilization_table=util,flow_table=flow_df,metadata={'scenario':scenario.to_dict(),'opened_hub_count':int((y>.5).sum()),'opened_hubs':[h for h,v in zip(hub_states,y) if v>.5],'demand_total':float(demand.demand_orders.sum()),'reconstructed_objective':reconstructed},raw_solver_result=raw)

def _model2_result(raw,demand,hubs,costs,scenario):
    supply=hubs['state'].tolist(); ds=demand['state'].tolist(); ni=len(supply); nj=len(ds)
    if not raw.success:
        return OptimizationResult('model2',_solver_status(raw),None,ValidationResult(False,{'solver_success':False},[str(raw.message)]),metadata={'scenario':scenario.to_dict()},raw_solver_result=raw)
    z=np.asarray(raw.x).reshape(ni,nj); D=demand.set_index('state')['demand_orders'].to_dict(); cap=hubs.set_index('state')['base_capacity_orders'].to_dict()
    cost_lookup={(r.origin_state,d):float(r[d]) for _,r in costs.iterrows() for d in ds}
    rows=[]
    for j,d in enumerate(ds):
        i=int(np.argmax(z[:,j])); c=cost_lookup[(supply[i],d)]; q=float(D[d]); rows.append({'customer_state':d,'assigned_seller_state':supply[i],'demand_orders':q,'cost_per_order':c,'assignment_cost':q*c})
    decision=pd.DataFrame(rows); used=decision.groupby('assigned_seller_state').demand_orders.sum().to_dict(); util=[]
    for s in supply:
        c=float(np.ceil(cap[s]*scenario.capacity_multiplier)); u=float(used.get(s,0)); util.append({'state':s,'capacity_orders':c,'orders_assigned':u,'utilization_pct':100*u/c if c else 0,'used':u>0})
    util=pd.DataFrame(util); transport=float(decision.assignment_cost.sum()); checks={'solver_success':True,'exactly_one_seller_per_customer_state':len(decision)==len(ds) and decision.customer_state.is_unique,'seller_capacity_respected':all(util.orders_assigned <= util.capacity_orders+1e-5),'objective_reconciles':abs(float(raw.fun)-transport)<1e-4}
    return OptimizationResult('model2','Optimal',float(raw.fun),ValidationResult(all(checks.values()),checks,[]),transport_cost=transport,decision_table=decision,utilization_table=util,metadata={'scenario':scenario.to_dict(),'seller_states_used_count':int(util.used.sum()),'seller_states_used':util.loc[util.used,'state'].tolist(),'customer_states':len(ds),'demand_total':float(demand.demand_orders.sum()),'capacity_total':float(util.capacity_orders.sum()),'reconstructed_objective':transport,'single_source':True},raw_solver_result=raw)

def run_model1(demand,hubs,cost_matrix,scenario):
    scenario.validate(); d=_scaled_demand(demand,scenario.demand_multiplier); c=_scaled_costs(cost_matrix,scenario.transport_cost_multiplier); return _model1_result(solve_cflp(d,hubs,c,scenario.capacity_multiplier,scenario.fixed_cost_per_hub,scenario.max_hubs),d,hubs,c,scenario)

def run_model2(demand,hubs,cost_matrix,scenario):
    scenario.validate(); d=_scaled_demand(demand,scenario.demand_multiplier); c=_scaled_costs(cost_matrix,scenario.transport_cost_multiplier); return _model2_result(solve_assignment(d,hubs,c,scenario.capacity_multiplier),d,hubs,c,scenario)

def run_model1_from_bundle(bundle,scenario): _require_valid_bundle(bundle); return run_model1(bundle.demand_table,bundle.candidate_hubs,bundle.cost_matrix,scenario)
def run_model2_from_bundle(bundle,scenario): _require_valid_bundle(bundle); return run_model2(bundle.demand_table,bundle.candidate_hubs,bundle.cost_matrix,scenario)
