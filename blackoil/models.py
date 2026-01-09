from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Scenario:
    name: str
    description: str
    grid_size: int
    max_days: int
    starting_cash: int
    land_cost: int
    drill_cost: int
    pump_cost: int
    storage_cost: int
    price_min: int
    price_max: int
    event_chance: float
    theme: str


@dataclass
class Tile:
    row: int
    col: int
    reserve: int
    output_rate: int
    owner: str | None = None
    drilled: bool = False
    pump_level: int = 0
    storage: int = 0
    capacity: int = 20
    survey_low: int | None = None
    survey_high: int | None = None

    @property
    def depleted(self) -> bool:
        return self.reserve <= 0

    @property
    def available_capacity(self) -> int:
        return max(0, self.capacity - self.storage)

    @property
    def has_pump(self) -> bool:
        return self.pump_level > 0

    @property
    def current_output(self) -> int:
        if not self.has_pump:
            return 0
        multiplier = 1 + (self.pump_level - 1) * 0.5
        return int(self.output_rate * multiplier)


@dataclass
class Competitor:
    name: str
    cash: int
    aggressiveness: float
    color: str
    storage_threshold: int
    risk_tolerance: float
    discipline: float


@dataclass
class Contract:
    name: str
    volume: int
    price: int
    days_remaining: int
    delivered: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.volume - self.delivered)


@dataclass
class Refinery:
    level: int = 0
    capacity: int = 0

    @property
    def active(self) -> bool:
        return self.level > 0


@dataclass
class TransportHub:
    level: int = 0

    @property
    def active(self) -> bool:
        return self.level > 0

    @property
    def delivery_bonus(self) -> float:
        return 0.05 * self.level

    @property
    def maintenance_discount(self) -> float:
        return 0.03 * self.level


@dataclass
class Buyer:
    name: str
    category: str
    demand: int
    multiplier: float
    reputation: int = 0

    def price_for(self, market_price: int) -> int:
        bonus = 1 + (self.reputation * 0.02)
        return max(1, int(market_price * self.multiplier * bonus))


@dataclass
class EconomySnapshot:
    production: int = 0
    refined: int = 0
    contract_delivered: int = 0
    maintenance_cost: int = 0
    interest_cost: int = 0
    events: list[str] = field(default_factory=list)
