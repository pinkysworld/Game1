from __future__ import annotations

from ..state import GameState
from .. import economy


def sell_oil(state: GameState) -> tuple[bool, str, int]:
    total_storage = economy.total_storage(state, "player")
    if total_storage <= 0:
        return False, "No oil to sell.", 0
    revenue = total_storage * state.price
    state.cash += revenue
    economy.withdraw_oil(state, total_storage)
    return True, f"Sold {total_storage} barrels.", revenue


def sell_petrol(state: GameState) -> tuple[bool, str, int]:
    if state.petrol_storage <= 0:
        return False, "No petrol to sell.", 0
    revenue = state.petrol_storage * state.petrol_price
    state.cash += revenue
    volume = state.petrol_storage
    state.petrol_storage = 0
    return True, f"Sold {volume} barrels of petrol.", revenue
