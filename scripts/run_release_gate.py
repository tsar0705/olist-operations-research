from pathlib import Path
from src.release import run_release_checks, release_ready
checks=run_release_checks(Path(__file__).resolve().parents[1])
for c in checks: print(('PASS' if c.passed else 'BLOCKED'), c.name, '-', c.detail)
raise SystemExit(0 if release_ready(checks) else 1)
