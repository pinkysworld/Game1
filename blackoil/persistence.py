from __future__ import annotations

import json
from pathlib import Path

from .models import Buyer, Competitor, Contract, Refinery, TransportHub
from .state import (
    BASE_DEMAND,
    DEFAULT_LOAN_LIMIT,
    DEFAULT_LOAN_RATE,
    PETROL_PRICE_MAX,
    PETROL_PRICE_MIN,
    SCENARIOS,
    create_buyers,
    create_competitors,
    create_decorations,
    create_tiles,
)
from .state import GameState

SAVE_VERSION = 2


def save_game(state: GameState, path: str | Path) -> None:
    data = {
        "save_version": SAVE_VERSION,
        "scenario": state.scenario.name,
        "day": state.day,
        "cash": state.cash,
        "price": state.price,
        "petrol_price": state.petrol_price,
        "event_message": state.event_message,
        "news_message": state.news_message,
        "loan_balance": state.loan_balance,
        "loan_limit": state.loan_limit,
        "loan_rate": state.loan_rate,
        "research_level": state.research_level,
        "auto_refine": state.auto_refine,
        "refinery": {"level": state.refinery.level, "capacity": state.refinery.capacity},
        "transport_hub": {"level": state.transport_hub.level},
        "total_oil_produced": state.total_oil_produced,
        "total_petrol_refined": state.total_petrol_refined,
        "total_contract_delivered": state.total_contract_delivered,
        "petrol_storage": state.petrol_storage,
        "day_phase": state.day_phase,
        "market_trend": state.market_trend,
        "market_supply": state.market_supply,
        "market_demand": state.market_demand,
        "last_day_production": state.last_day_production,
        "map_seed": state.map_seed,
        "decorations": state.decorations,
        "tiles": [
            {
                "row": tile.row,
                "col": tile.col,
                "reserve": tile.reserve,
                "output_rate": tile.output_rate,
                "owner": tile.owner,
                "drilled": tile.drilled,
                "pump_level": tile.pump_level,
                "storage": tile.storage,
                "capacity": tile.capacity,
                "survey_low": tile.survey_low,
                "survey_high": tile.survey_high,
            }
            for tile in state.tiles
        ],
        "competitors": [
            {
                "name": competitor.name,
                "cash": competitor.cash,
                "aggressiveness": competitor.aggressiveness,
                "color": competitor.color,
                "storage_threshold": competitor.storage_threshold,
                "risk_tolerance": competitor.risk_tolerance,
                "discipline": competitor.discipline,
            }
            for competitor in state.competitors
        ],
        "contracts": [
            {
                "name": contract.name,
                "volume": contract.volume,
                "price": contract.price,
                "days_remaining": contract.days_remaining,
                "delivered": contract.delivered,
            }
            for contract in state.contracts
        ],
        "buyers": [
            {
                "name": buyer.name,
                "category": buyer.category,
                "demand": buyer.demand,
                "multiplier": buyer.multiplier,
                "reputation": buyer.reputation,
            }
            for buyer in state.buyers
        ],
    }
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_game(path: str | Path) -> GameState:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    save_version = data.get("save_version", 1)

    scenario_name = data.get("scenario", SCENARIOS[0].name)
    scenario = next((s for s in SCENARIOS if s.name == scenario_name), SCENARIOS[0])

    map_seed = data.get("map_seed")
    if map_seed is None:
        map_seed = __import__("random").randint(1000, 9999)

    tiles_data = data.get("tiles")
    if tiles_data:
        tiles = [
            _tile_from_dict(item)
            for item in tiles_data
        ]
    else:
        tiles = create_tiles(scenario, map_seed)

    competitors_data = data.get("competitors")
    if competitors_data:
        competitors = [
            Competitor(
                name=item["name"],
                cash=item["cash"],
                aggressiveness=item["aggressiveness"],
                color=item["color"],
                storage_threshold=item.get("storage_threshold", 30),
                risk_tolerance=item.get("risk_tolerance", 0.5),
                discipline=item.get("discipline", 0.5),
            )
            for item in competitors_data
        ]
    else:
        competitors = create_competitors()

    contracts = [
        Contract(
            name=item["name"],
            volume=item["volume"],
            price=item["price"],
            days_remaining=item["days_remaining"],
            delivered=item.get("delivered", 0),
        )
        for item in data.get("contracts", [])
    ]

    buyers_data = data.get("buyers")
    if buyers_data:
        buyers = [
            Buyer(
                name=item["name"],
                category=item["category"],
                demand=item["demand"],
                multiplier=item["multiplier"],
                reputation=item.get("reputation", 0),
            )
            for item in buyers_data
        ]
    else:
        buyers = create_buyers()

    refinery_data = data.get("refinery", {})
    refinery = Refinery(
        level=refinery_data.get("level", 0),
        capacity=refinery_data.get("capacity", 0),
    )
    hub_data = data.get("transport_hub", {})
    hub = TransportHub(level=hub_data.get("level", 0))

    petrol_price = data.get("petrol_price", __import__("random").randint(PETROL_PRICE_MIN, PETROL_PRICE_MAX))

    state = GameState(
        scenario=scenario,
        day=data.get("day", 1),
        cash=data.get("cash", scenario.starting_cash),
        price=data.get("price", scenario.price_min),
        petrol_price=petrol_price,
        event_message=data.get("event_message", ""),
        news_message=data.get("news_message", ""),
        tiles=tiles,
        competitors=competitors,
        contracts=contracts,
        buyers=buyers,
        refinery=refinery,
        transport_hub=hub,
        loan_balance=data.get("loan_balance", 0),
        loan_limit=data.get("loan_limit", DEFAULT_LOAN_LIMIT),
        loan_rate=data.get("loan_rate", DEFAULT_LOAN_RATE),
        research_level=data.get("research_level", 0),
        auto_refine=data.get("auto_refine", True) if save_version >= 2 else True,
        total_oil_produced=data.get("total_oil_produced", 0),
        total_petrol_refined=data.get("total_petrol_refined", 0),
        total_contract_delivered=data.get("total_contract_delivered", 0),
        petrol_storage=data.get("petrol_storage", 0),
        day_phase=data.get("day_phase", 0),
        market_trend=data.get("market_trend", 0.0),
        market_supply=data.get("market_supply", 0),
        market_demand=data.get("market_demand", BASE_DEMAND),
        last_day_production=data.get("last_day_production", 0),
        map_seed=map_seed,
        decorations=data.get("decorations") or create_decorations(map_seed, scenario.grid_size),
    )
    return state


def _tile_from_dict(item: dict) -> "Tile":
    from .models import Tile

    return Tile(
        row=item["row"],
        col=item["col"],
        reserve=item["reserve"],
        output_rate=item["output_rate"],
        owner=item.get("owner"),
        drilled=item.get("drilled", False),
        pump_level=item.get("pump_level", 0),
        storage=item.get("storage", 0),
        capacity=item.get("capacity", 20),
        survey_low=item.get("survey_low"),
        survey_high=item.get("survey_high"),
    )
