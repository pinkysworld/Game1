from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OffshoreBlock:
    name: str
    water_depth: str
    metocean_severity: float
    rig_requirement: str


def downtime_probability(block: OffshoreBlock) -> float:
    base = 0.05
    if block.water_depth == "deep":
        base += 0.08
    return min(0.5, base + block.metocean_severity * 0.1)
