from __future__ import annotations

import random

from ..models import Tile
from ..state import GameState, MAX_PUMP_LEVEL, PUMP_UPGRADE_COST, SURVEY_COST


def survey_tile(state: GameState, tile: Tile) -> tuple[bool, str]:
    if tile.owner != "player":
        return False, "Tile not owned."
    if state.cash < SURVEY_COST:
        return False, "Insufficient cash to run a survey."
    state.cash -= SURVEY_COST
    if tile.reserve <= 0:
        low, high = 0, 10
    else:
        error = random.uniform(0.15, 0.35)
        low = max(0, int(tile.reserve * (1 - error)))
        high = int(tile.reserve * (1 + error))
    tile.survey_low = low
    tile.survey_high = high
    return True, f"Survey complete for ({tile.row + 1}, {tile.col + 1})."


def drill_well(state: GameState, tile: Tile) -> tuple[bool, str]:
    if tile.owner != "player":
        return False, "Tile not owned."
    if state.cash < state.scenario.drill_cost:
        return False, "Insufficient cash to drill."
    tile.drilled = True
    state.cash -= state.scenario.drill_cost
    if tile.reserve <= 0:
        return True, "Dry well! No oil in this tile."
    return True, f"Drilled well. Estimated reserves: {tile.reserve} barrels."


def build_pump(state: GameState, tile: Tile) -> tuple[bool, str]:
    if tile.owner != "player":
        return False, "Tile not owned."
    if tile.has_pump:
        return False, "Pump already installed."
    if state.cash < state.scenario.pump_cost:
        return False, "Insufficient cash to build pump."
    tile.pump_level = 1
    state.cash -= state.scenario.pump_cost
    return True, "Pump installed. Production will start next day."


def upgrade_pump(state: GameState, tile: Tile) -> tuple[bool, str]:
    if tile.owner != "player" or not tile.has_pump:
        return False, "Pump not installed."
    if tile.pump_level >= MAX_PUMP_LEVEL:
        return False, "Pump already at max level."
    if state.cash < PUMP_UPGRADE_COST:
        return False, "Insufficient cash to upgrade pump."
    tile.pump_level += 1
    state.cash -= PUMP_UPGRADE_COST
    return True, f"Pump upgraded to level {tile.pump_level}."
