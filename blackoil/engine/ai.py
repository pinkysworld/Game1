from __future__ import annotations

import random

from ..state import GameState, MAX_PUMP_LEVEL, PUMP_UPGRADE_COST


def competitor_turns(state: GameState) -> list[str]:
    events: list[str] = []
    for competitor in state.competitors:
        if random.random() < competitor.aggressiveness:
            _competitor_expand(state, competitor, events)
        _competitor_operate(state, competitor, events)
    return events


def _competitor_expand(state: GameState, competitor, events: list[str]) -> None:
    open_tiles = [tile for tile in state.tiles if tile.owner is None]
    if not open_tiles or competitor.cash < state.scenario.land_cost:
        return
    open_tiles.sort(key=lambda tile: tile.reserve, reverse=True)
    pick = random.randint(0, min(3, len(open_tiles) - 1))
    target = open_tiles[pick]
    target.owner = competitor.name
    competitor.cash -= state.scenario.land_cost
    events.append(f"{competitor.name} secured land at ({target.row + 1}, {target.col + 1}).")


def _competitor_operate(state: GameState, competitor, events: list[str]) -> None:
    price_ratio = state.price / state.scenario.price_max
    for tile in [tile for tile in state.tiles if tile.owner == competitor.name]:
        if not tile.drilled and competitor.cash >= state.scenario.drill_cost:
            tile.drilled = True
            competitor.cash -= state.scenario.drill_cost
        if tile.drilled and not tile.has_pump and competitor.cash >= state.scenario.pump_cost and tile.reserve > 0:
            tile.pump_level = 1
            competitor.cash -= state.scenario.pump_cost
        if tile.has_pump and tile.pump_level < MAX_PUMP_LEVEL and competitor.cash >= PUMP_UPGRADE_COST:
            if price_ratio > competitor.risk_tolerance:
                tile.pump_level += 1
                competitor.cash -= PUMP_UPGRADE_COST
        if tile.has_pump and tile.available_capacity < 10 and competitor.cash >= state.scenario.storage_cost:
            if price_ratio < (1 - competitor.discipline):
                tile.capacity += 10
                competitor.cash -= state.scenario.storage_cost

    storage = sum(tile.storage for tile in state.tiles if tile.owner == competitor.name)
    if storage >= competitor.storage_threshold and price_ratio > competitor.discipline:
        revenue = storage * state.price
        competitor.cash += revenue
        for tile in [tile for tile in state.tiles if tile.owner == competitor.name]:
            tile.storage = 0
        if storage > 0:
            events.append(f"{competitor.name} sold {storage} barrels for ${revenue}.")
