from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TransportOption:
    name: str
    capacity: int
    cost_per_barrel: float


def netback_price(market_price: int, transport: TransportOption) -> int:
    return max(1, int(market_price - transport.cost_per_barrel))
