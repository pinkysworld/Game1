from __future__ import annotations

from ..models import Tile
from ..state import GameState


def buy_land(state: GameState, tile: Tile) -> tuple[bool, str]:
    if tile.owner is not None:
        return False, "Tile already owned."
    if state.cash < state.scenario.land_cost:
        return False, "Insufficient cash to buy land."
    tile.owner = "player"
    state.cash -= state.scenario.land_cost
    return True, f"Bought land at ({tile.row + 1}, {tile.col + 1})."
