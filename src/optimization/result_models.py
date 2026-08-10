from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)


@dataclass
class OptimizationResult:
    model: str
    status: str
    objective_value: float | None
    validation: ValidationResult
    fixed_cost: float = 0.0
    transport_cost: float = 0.0
    decision_table: Any = None
    utilization_table: Any = None
    flow_table: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_solver_result: Any = None

    @property
    def success(self) -> bool:
        """Backward-compatible solver-success flag for Phase 2.2 callers."""
        return self.raw_solver_result is not None and bool(getattr(self.raw_solver_result, "success", False))

    @property
    def fun(self):
        """Backward-compatible raw objective accessor."""
        return self.objective_value

    @property
    def message(self) -> str:
        """Backward-compatible solver message."""
        if self.raw_solver_result is not None:
            return str(getattr(self.raw_solver_result, "message", self.status))
        return self.status

    @property
    def is_valid(self) -> bool:
        return self.validation.passed

    @property
    def is_optimal(self) -> bool:
        return self.status.lower() in {
            "optimal",
            "optimization terminated successfully",
            "highs status 7: optimal",
        }
