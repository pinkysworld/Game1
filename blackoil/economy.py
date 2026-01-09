from __future__ import annotations

import random

from .models import EconomySnapshot
from .state import (
    BASE_DEMAND,
    CONTRACT_PENALTY,
    DEMAND_VARIANCE,
    MARKET_IMPACT,
    MARKET_TREND_MAX,
    PETROL_PRICE_MAX,
    PETROL_PRICE_MIN,
    MAINTENANCE_COST,
)
from .state import GameState


def apply_market(state: GameState) -> None:
    supply_pressure = max(-50, min(50, state.market_demand - state.market_supply))
    delta = (state.market_trend * 6) + (supply_pressure * MARKET_IMPACT) + random.randint(-10, 10)
    state.price = int(state.price + delta)
    state.price = max(state.scenario.price_min, min(state.scenario.price_max, state.price))


def apply_petrol_market(state: GameState) -> None:
    delta = random.randint(-10, 10) + int((state.price - state.scenario.price_min) * 0.1)
    state.petrol_price = max(PETROL_PRICE_MIN, min(PETROL_PRICE_MAX, state.petrol_price + delta))


def update_market_conditions(state: GameState) -> None:
    shock = random.uniform(-0.6, 0.6)
    state.market_trend = max(-MARKET_TREND_MAX, min(MARKET_TREND_MAX, state.market_trend + shock))
    trend_bias = int(state.market_trend * 18)
    state.market_demand = max(40, BASE_DEMAND + trend_bias + random.randint(-DEMAND_VARIANCE, DEMAND_VARIANCE))
    state.market_supply = state.last_day_production


def produce_oil(state: GameState, snapshot: EconomySnapshot) -> None:
    state.last_day_production = 0
    for tile in state.tiles:
        if tile.has_pump and tile.reserve > 0 and tile.available_capacity > 0:
            output = min(tile.current_output, tile.reserve, tile.available_capacity)
            tile.reserve -= output
            tile.storage += output
            snapshot.production += output
            state.total_oil_produced += output
            state.last_day_production += output
            if tile.reserve == 0:
                snapshot.events.append(
                    f"Well at ({tile.row + 1}, {tile.col + 1}) ran dry. Storage holds {tile.storage} barrels."
                )


def refine_oil(state: GameState, snapshot: EconomySnapshot) -> None:
    if not state.refinery.active or not state.auto_refine:
        return
    available_oil = total_storage(state, "player")
    if available_oil <= 0:
        return
    refine_amount = min(available_oil, state.refinery.capacity)
    withdraw_oil(state, refine_amount)
    state.petrol_storage += refine_amount
    snapshot.refined += refine_amount
    state.total_petrol_refined += refine_amount
    snapshot.events.append(f"Refined {refine_amount} barrels into petrol.")


def process_contracts(state: GameState, snapshot: EconomySnapshot) -> None:
    if not state.contracts:
        return
    for contract in list(state.contracts):
        deliverable = min(contract.remaining, total_storage(state, "player"))
        if deliverable > 0:
            withdraw_oil(state, deliverable)
            contract.delivered += deliverable
            state.total_contract_delivered += deliverable
            bonus = 1 + state.transport_hub.delivery_bonus
            revenue = int(deliverable * contract.price * bonus)
            state.cash += revenue
            snapshot.contract_delivered += deliverable
            snapshot.events.append(
                f"Delivered {deliverable} barrels to {contract.name} for ${revenue}."
            )
        contract.days_remaining -= 1
        if contract.days_remaining <= 0:
            if contract.remaining > 0:
                state.cash = max(0, state.cash - CONTRACT_PENALTY)
                snapshot.events.append(
                    f"Missed contract with {contract.name}. Penalty: ${CONTRACT_PENALTY}."
                )
            state.contracts.remove(contract)


def maintenance_and_interest(state: GameState, snapshot: EconomySnapshot) -> None:
    pump_count = sum(1 for tile in state.tiles if tile.owner == "player" and tile.has_pump)
    refinery_cost = MAINTENANCE_COST if state.refinery.active else 0
    base = MAINTENANCE_COST + refinery_cost + pump_count * 15
    efficiency = 1 - min(0.3, state.research_level * 0.03) - state.transport_hub.maintenance_discount
    cost = int(max(0.5, efficiency) * base)
    if cost > 0:
        state.cash = max(0, state.cash - cost)
        snapshot.maintenance_cost = cost
    if state.loan_balance > 0:
        interest = int(state.loan_balance * state.loan_rate)
        state.loan_balance += interest
        snapshot.interest_cost = interest


def random_event(state: GameState, snapshot: EconomySnapshot) -> None:
    if random.random() > state.scenario.event_chance:
        state.event_message = ""
        return
    roll = random.random()
    if roll < 0.35:
        loss = random.randint(150, 450)
        state.cash = max(0, state.cash - loss)
        state.event_message = f"Equipment repairs cost ${loss}."
    elif roll < 0.65:
        bonus = random.randint(120, 480)
        state.cash += bonus
        state.event_message = f"Pipeline bonus payout: ${bonus}."
    else:
        if state.price < state.scenario.price_max:
            state.price += 12
            state.event_message = "Rumors of shortage raise oil prices."
    if state.event_message:
        snapshot.events.append(state.event_message)


def advance_day(state: GameState) -> EconomySnapshot:
    snapshot = EconomySnapshot()
    produce_oil(state, snapshot)
    process_contracts(state, snapshot)
    refine_oil(state, snapshot)
    update_market_conditions(state)
    apply_market(state)
    apply_petrol_market(state)
    random_event(state, snapshot)
    maintenance_and_interest(state, snapshot)
    state.day_phase = (state.day_phase + 1) % 4
    return snapshot


def total_storage(state: GameState, owner: str) -> int:
    return sum(tile.storage for tile in state.tiles if tile.owner == owner)


def withdraw_oil(state: GameState, amount: int) -> None:
    remaining = amount
    for tile in [tile for tile in state.tiles if tile.owner == "player"]:
        if remaining <= 0:
            break
        if tile.storage <= remaining:
            remaining -= tile.storage
            tile.storage = 0
        else:
            tile.storage -= remaining
            remaining = 0
