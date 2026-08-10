# Phase 2.12 — Final UI Polish + Release Hardening

## Objective

Finish the Streamlit dashboard presentation layer and make deployment failures
explicit rather than silent. The architecture continues to require Streamlit to
remain a thin presentation/orchestration layer over the validated Phase 1
pipeline.

## Implemented

### 1. Release-hardened application entry point

`app.py` now:

- sets a stable page title/icon/layout;
- applies shared dashboard styling;
- shows dataset readiness and fingerprint in the sidebar;
- provides a transient-session reset control;
- lazy-loads page modules so a partial deployment can still open diagnostics;
- routes all Phase 2 pages, including Model Comparison & Downloads;
- keeps optimization/geography/prototype logic out of the entry point.

### 2. Shared UI polish

Added `src/ui/theme.py` with reusable presentation primitives for:

- consistent page spacing;
- metric-card treatment;
- section headers;
- status messaging.

Added `.streamlit/config.toml` for consistent application appearance.

### 3. Release diagnostics

Added `src/release.py` and `src/ui/release_status.py`.

The release screen checks:

- required runtime dependencies;
- required Phase 1/Phase 2 source modules;
- thin-entry-point architecture constraints.

A deployment is **not** called release-ready when analytical modules or runtime
dependencies are missing.

### 4. Configuration and package hygiene

Added:

- `src/config.py` with the nine real Olist source filenames;
- package `__init__.py` files;
- scenario-aware cache/session support carried forward from the earlier Phase 2
  contracts;
- a minimum dashboard `requirements.txt`.

Synthetic/demo data remains explicitly excluded from the final application.

### 5. Phase 2.12 regression tests

Added `tests/test_phase2_12.py` covering:

- thin application entry point;
- release diagnostic behavior;
- release status page;
- nine-file configuration;
- shared UI primitives;
- no-demo-data release messaging.

## Validation

### Automated tests

```text
20 passed
2 skipped
```

The two skips are the existing optional Streamlit `AppTest` smoke tests. The
current execution environment does not have Streamlit installed, so a live UI
pass is not claimed.

### Release diagnostic

Current archive check:

```text
BLOCKED dependency:streamlit
BLOCKED src/optimization/model2_assignment.py
BLOCKED src/validation/data_checks.py
```

The remaining dashboard/runtime tree in the milestone archive is therefore **not
claimed to be a fully runnable production release**. The new release diagnostics
surface those blockers explicitly.

## Source-derived architecture preserved

The Phase 2 architecture requires:

- real Olist data only;
- no hard-coded geographic coordinates in the dashboard;
- no synthetic fallback;
- canonical Phase 1 data as the source of truth;
- validated optimization results before presentation;
- Phase 1.4 calibrated transportation costs;
- real Olist-derived coordinates for maps;
- downloadable results;
- existing Phase 1 tests remaining green.

Phase 2.12 changes the presentation and release layer without replacing those
analytical contracts.

## Acceptance status

**Phase 2.12 implementation: complete.**

**Full production release acceptance: pending the complete Phase 1/Phase 2
runtime tree and Streamlit environment.**

This distinction is intentional: release hardening should expose missing
runtime pieces, not hide them behind a green dashboard.
