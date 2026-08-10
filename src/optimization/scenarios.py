from dataclasses import dataclass, replace

@dataclass(frozen=True)
class Scenario:
    """Explicit parameters shared by dashboard optimization experiments."""
    capacity_multiplier: float = 1.20
    fixed_cost_per_hub: float = 50_000.0
    max_hubs: int | None = None
    demand_multiplier: float = 1.00
    transport_cost_multiplier: float = 1.00

    def with_updates(self, **kwargs):
        return replace(self, **kwargs)

    def to_dict(self):
        return {
            "capacity_multiplier": self.capacity_multiplier,
            "fixed_cost_per_hub": self.fixed_cost_per_hub,
            "max_hubs": self.max_hubs,
            "demand_multiplier": self.demand_multiplier,
            "transport_cost_multiplier": self.transport_cost_multiplier,
        }

    def validate(self):
        if self.capacity_multiplier <= 0:
            raise ValueError("capacity_multiplier must be > 0")
        if self.fixed_cost_per_hub < 0:
            raise ValueError("fixed_cost_per_hub must be >= 0")
        if self.max_hubs is not None and self.max_hubs < 1:
            raise ValueError("max_hubs must be >= 1 or None")
        if self.demand_multiplier <= 0:
            raise ValueError("demand_multiplier must be > 0")
        if self.transport_cost_multiplier <= 0:
            raise ValueError("transport_cost_multiplier must be > 0")
        return self
