from __future__ import annotations

from dataclasses import dataclass, field

from .models import Buyer, Competitor, Contract, Refinery, Scenario, Tile, TransportHub

OIL_PER_DAY_MIN = 6
OIL_PER_DAY_MAX = 22
MAX_PUMP_LEVEL = 3
SURVEY_COST = 350
PUMP_UPGRADE_COST = 700
STORAGE_EXPANSION = 15
LOAN_CHUNK = 2000
DEFAULT_LOAN_LIMIT = 6000
DEFAULT_LOAN_RATE = 0.06
RESEARCH_COST = 500
MAINTENANCE_COST = 120
CONTRACT_PENALTY = 250
REFINERY_BUILD_COST = 3200
REFINERY_UPGRADE_COST = 1800
REFINERY_BASE_CAPACITY = 40
PETROL_PRICE_MIN = 55
PETROL_PRICE_MAX = 160
HUB_BUILD_COST = 1800
HUB_UPGRADE_COST = 900
HUB_MAX_LEVEL = 3
BASE_DEMAND = 120
DEMAND_VARIANCE = 45
MARKET_TREND_MAX = 2.5
MARKET_IMPACT = 0.35
TRADE_MIN_VOLUME = 20
TRADE_MAX_VOLUME = 120
REPUTATION_MAX = 5
MAP_PIXEL_SIZE = 560

SCENARIOS = [
    Scenario(
        name="Frontier Boom",
        description="Balanced market with steady reserves and moderate costs.",
        grid_size=5,
        max_days=30,
        starting_cash=5200,
        land_cost=600,
        drill_cost=800,
        pump_cost=1200,
        storage_cost=200,
        price_min=30,
        price_max=120,
        event_chance=0.35,
        theme="prairie",
    ),
    Scenario(
        name="Desert Wildcat",
        description="Higher drilling costs and sparser oil, but bigger price swings.",
        grid_size=6,
        max_days=28,
        starting_cash=6200,
        land_cost=700,
        drill_cost=1000,
        pump_cost=1400,
        storage_cost=240,
        price_min=25,
        price_max=150,
        event_chance=0.4,
        theme="desert",
    ),
    Scenario(
        name="Coastal Rush",
        description="Compact grid, high reserves, and fierce competition.",
        grid_size=4,
        max_days=24,
        starting_cash=4500,
        land_cost=650,
        drill_cost=900,
        pump_cost=1300,
        storage_cost=220,
        price_min=35,
        price_max=110,
        event_chance=0.32,
        theme="coastal",
    ),
]


@dataclass
class GameState:
    scenario: Scenario
    day: int
    cash: int
    price: int
    petrol_price: int
    event_message: str
    news_message: str
    tiles: list[Tile]
    competitors: list[Competitor]
    contracts: list[Contract]
    buyers: list[Buyer]
    refinery: Refinery
    transport_hub: TransportHub
    loan_balance: int
    loan_limit: int
    loan_rate: float
    research_level: int
    auto_refine: bool
    total_oil_produced: int
    total_petrol_refined: int
    total_contract_delivered: int
    petrol_storage: int
    day_phase: int
    market_trend: float
    market_supply: int
    market_demand: int
    last_day_production: int
    map_seed: int
    decorations: list[tuple[int, int, int, str]]


def create_competitors() -> list[Competitor]:
    return [
        Competitor("Iron Ridge", 4200, 0.55, "#ef4444", 35, 0.7, 0.6),
        Competitor("Desert Drill", 3800, 0.45, "#f97316", 30, 0.55, 0.5),
        Competitor("Silver Creek", 3400, 0.4, "#a855f7", 28, 0.45, 0.7),
    ]


def create_buyers() -> list[Buyer]:
    return [
        Buyer("Kingston Rail", "Company", 140, 1.05),
        Buyer("Northern Navy", "Nation", 160, 1.1),
        Buyer("Harbor Authority", "Company", 120, 1.0),
        Buyer("Imperial Trade Office", "Nation", 110, 1.12),
        Buyer("Frontier Republic", "Nation", 100, 0.98),
    ]


def create_tiles(scenario: Scenario, rng_seed: int) -> list[Tile]:
    tiles: list[Tile] = []
    rng = __import__("random").Random(rng_seed)
    for row in range(scenario.grid_size):
        for col in range(scenario.grid_size):
            reserve = rng.randint(0, 170)
            tiles.append(
                Tile(
                    row=row,
                    col=col,
                    reserve=reserve,
                    output_rate=rng.randint(OIL_PER_DAY_MIN, OIL_PER_DAY_MAX),
                )
            )
    return tiles


def create_decorations(seed: int, grid_size: int) -> list[tuple[int, int, int, str]]:
    rng = __import__("random").Random(seed)
    decorations = []
    for _ in range(grid_size * grid_size * 3):
        x = rng.randint(0, 599)
        y = rng.randint(0, 599)
        size = rng.randint(4, 12)
        color = rng.choice(["#0f172a", "#1e293b", "#334155", "#0f172a"])
        decorations.append((x, y, size, color))
    return decorations


def new_game_state(scenario: Scenario) -> GameState:
    rng = __import__("random")
    map_seed = rng.randint(1000, 9999)
    tiles = create_tiles(scenario, map_seed)
    return GameState(
        scenario=scenario,
        day=1,
        cash=scenario.starting_cash,
        price=rng.randint(scenario.price_min, scenario.price_max),
        petrol_price=rng.randint(PETROL_PRICE_MIN, PETROL_PRICE_MAX),
        event_message="",
        news_message="",
        tiles=tiles,
        competitors=create_competitors(),
        contracts=[],
        buyers=create_buyers(),
        refinery=Refinery(),
        transport_hub=TransportHub(),
        loan_balance=0,
        loan_limit=DEFAULT_LOAN_LIMIT,
        loan_rate=DEFAULT_LOAN_RATE,
        research_level=0,
        auto_refine=True,
        total_oil_produced=0,
        total_petrol_refined=0,
        total_contract_delivered=0,
        petrol_storage=0,
        day_phase=0,
        market_trend=0.0,
        market_supply=0,
        market_demand=BASE_DEMAND,
        last_day_production=0,
        map_seed=map_seed,
        decorations=create_decorations(map_seed, scenario.grid_size),
    )


def buy_land(state: GameState, tile: Tile) -> bool:
    if tile.owner is not None or state.cash < state.scenario.land_cost:
        return False
    tile.owner = "player"
    state.cash -= state.scenario.land_cost
    return True


def survey_tile(state: GameState, tile: Tile) -> tuple[int, int] | None:
    if tile.owner != "player" or state.cash < SURVEY_COST:
        return None
    state.cash -= SURVEY_COST
    if tile.reserve <= 0:
        low, high = 0, 10
    else:
        rng = __import__("random")
        error = rng.uniform(0.15, 0.35)
        low = max(0, int(tile.reserve * (1 - error)))
        high = int(tile.reserve * (1 + error))
    tile.survey_low = low
    tile.survey_high = high
    return low, high


def drill_well(state: GameState, tile: Tile) -> bool:
    if tile.owner != "player" or state.cash < state.scenario.drill_cost:
        return False
    tile.drilled = True
    state.cash -= state.scenario.drill_cost
    return True


def build_pump(state: GameState, tile: Tile) -> bool:
    if tile.owner != "player" or state.cash < state.scenario.pump_cost:
        return False
    tile.pump_level = 1
    state.cash -= state.scenario.pump_cost
    return True


def upgrade_pump(state: GameState, tile: Tile) -> bool:
    if tile.owner != "player" or not tile.has_pump or tile.pump_level >= MAX_PUMP_LEVEL:
        return False
    if state.cash < PUMP_UPGRADE_COST:
        return False
    tile.pump_level += 1
    state.cash -= PUMP_UPGRADE_COST
    return True


def add_storage(state: GameState, tile: Tile) -> bool:
    if tile.owner != "player" or state.cash < state.scenario.storage_cost:
        return False
    tile.capacity += STORAGE_EXPANSION
    state.cash -= state.scenario.storage_cost
    return True


def build_refinery(state: GameState) -> bool:
    if state.refinery.active or state.cash < REFINERY_BUILD_COST:
        return False
    state.cash -= REFINERY_BUILD_COST
    state.refinery.level = 1
    state.refinery.capacity = REFINERY_BASE_CAPACITY
    return True


def upgrade_refinery(state: GameState) -> bool:
    if not state.refinery.active or state.cash < REFINERY_UPGRADE_COST:
        return False
    state.cash -= REFINERY_UPGRADE_COST
    state.refinery.level += 1
    state.refinery.capacity += int(REFINERY_BASE_CAPACITY * 0.6)
    return True


def research_upgrade(state: GameState) -> bool:
    if state.cash < RESEARCH_COST:
        return False
    state.cash -= RESEARCH_COST
    state.research_level += 1
    return True


def build_hub(state: GameState) -> bool:
    if state.transport_hub.active or state.cash < HUB_BUILD_COST:
        return False
    state.cash -= HUB_BUILD_COST
    state.transport_hub.level = 1
    return True


def upgrade_hub(state: GameState) -> bool:
    if not state.transport_hub.active or state.transport_hub.level >= HUB_MAX_LEVEL:
        return False
    if state.cash < HUB_UPGRADE_COST:
        return False
    state.cash -= HUB_UPGRADE_COST
    state.transport_hub.level += 1
    return True


def take_loan(state: GameState) -> int:
    if state.loan_balance >= state.loan_limit:
        return 0
    amount = min(LOAN_CHUNK, state.loan_limit - state.loan_balance)
    state.cash += amount
    state.loan_balance += amount
    return amount


def repay_loan(state: GameState) -> int:
    if state.loan_balance <= 0:
        return 0
    amount = min(LOAN_CHUNK, state.loan_balance)
    if state.cash < amount:
        return 0
    state.cash -= amount
    state.loan_balance -= amount
    return amount


def sell_oil(state: GameState, volume: int, price: int) -> int:
    if volume <= 0:
        return 0
    revenue = volume * price
    state.cash += revenue
    return revenue


def sell_petrol(state: GameState, volume: int, price: int) -> int:
    if volume <= 0:
        return 0
    revenue = volume * price
    state.cash += revenue
    state.petrol_storage -= volume
    return revenue


def sign_contract(state: GameState, contract: Contract, volume: int) -> Contract:
    contract.volume = volume
    state.contracts.append(contract)
    return contract


def apply_trade(state: GameState, buyer: Buyer, volume: int, commodity: str, market_price: int) -> int:
    if volume <= 0:
        return 0
    price = buyer.price_for(market_price)
    revenue = volume * price
    state.cash += revenue
    buyer.demand = max(0, buyer.demand - volume)
    buyer.reputation = min(REPUTATION_MAX, buyer.reputation + 1)
    if commodity == "petrol":
        state.petrol_storage -= volume
    return revenue
