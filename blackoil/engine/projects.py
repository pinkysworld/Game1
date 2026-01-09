from __future__ import annotations

from dataclasses import dataclass

from ..models import Refinery, TransportHub
from ..state import (
    GameState,
    HUB_BUILD_COST,
    HUB_MAX_LEVEL,
    HUB_UPGRADE_COST,
    REFINERY_BASE_CAPACITY,
    REFINERY_BUILD_COST,
    REFINERY_UPGRADE_COST,
    RESEARCH_COST,
)


@dataclass
class Project:
    name: str
    duration_days: int
    remaining_days: int
    cost: int
    status: str = "planned"

    def tick(self) -> None:
        if self.status != "active":
            return
        if self.remaining_days > 0:
            self.remaining_days -= 1
        if self.remaining_days == 0:
            self.status = "complete"


def build_refinery(state: GameState) -> tuple[bool, str]:
    if state.refinery.active:
        return False, "Refinery already built."
    if state.cash < REFINERY_BUILD_COST:
        return False, "Insufficient cash to build refinery."
    state.cash -= REFINERY_BUILD_COST
    state.refinery = Refinery(level=1, capacity=REFINERY_BASE_CAPACITY)
    return True, "Refinery built."


def upgrade_refinery(state: GameState) -> tuple[bool, str]:
    if not state.refinery.active:
        return False, "No refinery to upgrade."
    if state.cash < REFINERY_UPGRADE_COST:
        return False, "Insufficient cash to upgrade refinery."
    state.cash -= REFINERY_UPGRADE_COST
    state.refinery.level += 1
    state.refinery.capacity += int(REFINERY_BASE_CAPACITY * 0.6)
    return True, f"Refinery upgraded to level {state.refinery.level}."


def build_hub(state: GameState) -> tuple[bool, str]:
    if state.transport_hub.active:
        return False, "Transport hub already built."
    if state.cash < HUB_BUILD_COST:
        return False, "Insufficient cash to build transport hub."
    state.cash -= HUB_BUILD_COST
    state.transport_hub = TransportHub(level=1)
    return True, "Transport hub constructed."


def upgrade_hub(state: GameState) -> tuple[bool, str]:
    if not state.transport_hub.active:
        return False, "No transport hub to upgrade."
    if state.transport_hub.level >= HUB_MAX_LEVEL:
        return False, "Transport hub already at max level."
    if state.cash < HUB_UPGRADE_COST:
        return False, "Insufficient cash to upgrade hub."
    state.cash -= HUB_UPGRADE_COST
    state.transport_hub.level += 1
    return True, f"Transport hub upgraded to level {state.transport_hub.level}."


def research_upgrade(state: GameState) -> tuple[bool, str]:
    if state.cash < RESEARCH_COST:
        return False, "Insufficient cash to fund research."
    state.cash -= RESEARCH_COST
    state.research_level += 1
    return True, "Research complete. Efficiency improved."
