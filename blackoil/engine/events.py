from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Incident:
    name: str
    severity: float
    downtime_days: int


def sample_incident(seed: int) -> Incident | None:
    import random

    rng = random.Random(seed)
    roll = rng.random()
    if roll < 0.05:
        return Incident("Lost circulation", 0.6, 2)
    if roll < 0.08:
        return Incident("Equipment failure", 0.4, 1)
    if roll < 0.1:
        return Incident("Weather downtime", 0.3, 1)
    return None
