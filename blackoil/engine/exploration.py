from __future__ import annotations

import random

from .geology import Prospect, reduce_uncertainty


def run_recon(prospect: Prospect, seed: int) -> Prospect:
    rng = random.Random(seed)
    factor = rng.uniform(0.75, 0.9)
    prospect.estimate = reduce_uncertainty(prospect.estimate, factor)
    return prospect


def run_2d_seismic(prospect: Prospect, seed: int) -> Prospect:
    rng = random.Random(seed)
    factor = rng.uniform(0.55, 0.7)
    prospect.estimate = reduce_uncertainty(prospect.estimate, factor)
    return prospect


def run_3d_seismic(prospect: Prospect, seed: int) -> Prospect:
    rng = random.Random(seed)
    factor = rng.uniform(0.3, 0.5)
    prospect.estimate = reduce_uncertainty(prospect.estimate, factor)
    return prospect
