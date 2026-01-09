from __future__ import annotations

import random

from ..models import Buyer, Contract
from ..state import GameState, TRADE_MAX_VOLUME, TRADE_MIN_VOLUME


def trade_offers(state: GameState) -> list[Buyer]:
    rng = random.Random(state.map_seed + state.day)
    offers = rng.sample(state.buyers, k=min(3, len(state.buyers)))
    for buyer in offers:
        buyer.demand = max(TRADE_MIN_VOLUME, min(TRADE_MAX_VOLUME, buyer.demand + rng.randint(-20, 20)))
    return offers


def contract_offers(state: GameState) -> list[Contract]:
    offers = []
    base_volume = random.randint(60, 140)
    for _ in range(3):
        volume = base_volume + random.randint(-20, 40)
        price = max(state.price + random.randint(-5, 25), state.scenario.price_min)
        duration = random.randint(3, 7)
        offers.append(
            Contract(
                name=random.choice(["Rail Consortium", "Harbor Authority", "Frontier Army", "Steel Works"]),
                volume=volume,
                price=price,
                days_remaining=duration,
            )
        )
    return offers
