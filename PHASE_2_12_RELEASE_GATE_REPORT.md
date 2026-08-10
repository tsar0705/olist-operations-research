# Phase 2.12 — Runtime Blocker Closure + Release Gate

## Scope

Closed the previously reported runtime-tree blockers and executed the real Olist analytical pipeline against the nine Olist CSVs available in `<local-project-data>`.

## Blockers closed

- `src/optimization/model2_assignment.py` restored into the release tree.
- `src/validation/data_checks.py` restored/implemented for canonical-input validation.
- Phase 1 runtime dependencies restored: `olist_preprocessing.py`, `geography.py`, `phase1_service.py`.
- Phase 1.4 calibration artifact bundled under `phase1_outputs/PHASE_1_4_CALIBRATION.json`.
- Sensitivity engine restored as the proper package module `src/analytics/sensitivity.py`.
- Optimization service corrected to return the structured `OptimizationResult` contract consumed by the UI.
- Live Olist end-to-end regression test added.
- Streamlit AppTest smoke tests added and will execute automatically when Streamlit is installed.

## Full Olist end-to-end result

- Canonical bundle: PASS
- Total orders: **99,441**
- Customer states: **27**
- Candidate seller states: **23**
- Transportation lanes: **621**
- Model 1: **valid optimal**, objective `2,254,243.1384`
  - Fixed cost: `150,000`
  - Transport cost: `2,104,243.1384`
  - Opened hubs: `SP, MG, PR`
- Model 2: **valid optimal**, objective `2,052,400.8030`
  - Transport cost: `2,052,400.8030`
  - Seller states used: `13`
- Model comparison: PASS
- Corrected transport-only capacity monotonicity benchmark: PASS

These figures match the Phase 1 / Phase 2 analytical contract: demand is unique Olist orders by customer state, candidate hubs are seller states, and transportation cost uses the Phase 1.4 calibrated profile.

## Automated test result

```text
21 passed, 4 skipped
```

The four skips are the new/previous Streamlit AppTest tests. The current execution image does **not** contain the Streamlit package, and the configured package index does not expose a Streamlit wheel, so a genuine AppTest execution cannot honestly be claimed from this environment.

## Release gate

All project/runtime-tree checks now pass except the environment dependency:

```text
BLOCKED dependency:streamlit - not installed
```

Everything else is green, including:

- Model 2 solver module
- canonical data validation
- Phase 1 service
- sensitivity package
- Phase 1.4 calibration artifact
- thin-entry-point architecture

## Final acceptance state

**Analytical runtime tree: READY.**

**Production release gate: BLOCKED only by missing Streamlit in the execution environment.**

Once Streamlit `>=1.35,<2` is installed in a normal Python environment, run:

```text
python scripts/run_release_gate.py
pytest -q
```

The AppTest tests are then expected to execute instead of being skipped.

For the actual deployment machine, the final gate is therefore intentionally binary: install the declared Streamlit dependency, run the gate, then perform the live AppTest smoke tests.
