from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class ReservoirTruth:
    thickness: float
    porosity: float
    permeability: float
    trap_size: float
    oil_in_place: float
    drive_mechanism: str


@dataclass
class ProspectEstimate:
    pos: float
    p10: float
    p50: float
    p90: float
    depth: float
    fluid_type: str


@dataclass
class Prospect:
    name: str
    estimate: ProspectEstimate
    truth: ReservoirTruth


def generate_prospect(seed: int, name: str) -> Prospect:
    rng = random.Random(seed)
    truth = ReservoirTruth(
        thickness=rng.uniform(8, 55),
        porosity=rng.uniform(0.12, 0.28),
        permeability=rng.uniform(20, 450),
        trap_size=rng.uniform(1.2, 9.0),
        oil_in_place=rng.uniform(18, 220),
        drive_mechanism=rng.choice(["solution gas", "water drive", "gas cap", "mixed drive"]),
    )
    pos = rng.uniform(0.2, 0.65)
    p50 = truth.oil_in_place * rng.uniform(0.8, 1.2)
    p10 = p50 * rng.uniform(1.4, 1.8)
    p90 = p50 * rng.uniform(0.4, 0.7)
    estimate = ProspectEstimate(
        pos=pos,
        p10=max(p10, p50),
        p50=p50,
        p90=min(p90, p50),
        depth=rng.uniform(2200, 4200),
        fluid_type=rng.choice(["oil", "gas", "condensate"]),
    )
    return Prospect(name=name, estimate=estimate, truth=truth)


def reduce_uncertainty(estimate: ProspectEstimate, factor: float) -> ProspectEstimate:
    factor = max(0.1, min(0.9, factor))
    span = estimate.p10 - estimate.p90
    shrink = span * factor
    p50 = estimate.p50
    return ProspectEstimate(
        pos=min(0.9, estimate.pos + (1 - estimate.pos) * 0.1),
        p10=p50 + shrink / 2,
        p50=p50,
        p90=p50 - shrink / 2,
        depth=estimate.depth,
        fluid_type=estimate.fluid_type,
    )
