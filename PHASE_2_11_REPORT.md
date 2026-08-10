# Phase 2.11 — End-to-End Dashboard Tests

## Objective

Validate the complete Phase 2 dashboard flow and harden the integration between
navigation, dataset validation, canonical state, optimization pages,
sensitivity analysis, and Phase 2.10 comparison/downloads.

## Implemented

### 1. Navigation integration hardening

The main `app.py` now explicitly exposes:

- Dataset Upload & Validation
- Model 1 — Facility Location
- Model 2 — Seller Assignment
- Sensitivity Analysis
- Model Comparison & Downloads
- Architecture Status

The comparison page is imported and routed by the application rather than
existing only as an orphaned module.

### 2. End-to-end contract tests

Added `tests/test_phase2_11.py` covering the complete dashboard contract:

- all Phase 2 pages are reachable from navigation;
- `app.py` remains an orchestration layer and contains no prototype coordinates,
  synthetic fallback, Haversine calculation, or solver implementation;
- the upload page enforces the nine-file/schema gate before canonical validation;
- invalid canonical data blocks Model 1, Model 2, and sensitivity execution;
- Model 1 and Model 2 use the optimization service boundary and scenario cache;
- the comparison page consumes validated stored results and does not solve models;
- comparison/download exports include all required Phase 2.10 result artifacts;
- Phase 2.10 comparison logic remains green as part of the Phase 2.11 suite.

### 3. Real UI smoke-test hook

Two Streamlit `AppTest` tests are included. They run automatically in the
complete application environment and intentionally skip when Streamlit is not
installed. This keeps minimal CI honest: it does not fake Streamlit merely to
claim a UI test passed.

## Architecture basis

The Phase 2 architecture requires nine real Olist source tables, schema and
referential validation, canonical preprocessing, validated optimization,
sensitivity analysis, real Olist-derived geography, and downloadable results.
It also explicitly defines Phase 2.11 as the end-to-end dashboard-test stage.

The production flow is therefore tested as a contract:

```text
9 Olist CSV uploads
        ↓
required-file + schema gate
        ↓
Phase 1 canonical bundle
        ↓
validated Model 1 / Model 2
        ↓
sensitivity analysis
        ↓
validated comparison
        ↓
CSV + ZIP downloads
```

## Validation

In the available execution environment:

- source compilation: PASS;
- Phase 2.10 comparison tests: PASS;
- Phase 2.11 source/integration contract tests: PASS;
- real Streamlit AppTest: NOT EXECUTED because Streamlit is not installed;
- full optimization runtime: NOT EXECUTED because the available environment
  also lacks the project's solver/runtime dependency set.

This is an environment limitation, not a fabricated UI pass.

## Important finding

The Phase 2.10 package supplied for this milestone contains the Phase 2.10/2.9
changed files but not the complete Phase 1/Phase 2 dependency tree. Therefore a
true live-dashboard run cannot be honestly claimed from this package alone.
The tests are structured so the AppTest smoke tests become executable as soon
as the complete project tree and runtime dependencies are present.

## Acceptance status

Phase 2.11 integration hardening: **implemented**.

Full live end-to-end acceptance: **pending complete runtime environment**.

## Next

Phase 2.12 — final UI polish and release hardening.
