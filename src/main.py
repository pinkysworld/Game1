import json
import random
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

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

    def will_expand(self) -> bool:
        return random.random() < self.aggressiveness


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


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event: tk.Event) -> None:
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip,
            text=self.text,
            background="#111827",
            foreground="#f8fafc",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Helvetica", 9),
            padx=6,
            pady=2,
        )
        label.pack()

    def _hide(self, _event: tk.Event) -> None:
        if self.tip:
            self.tip.destroy()
            self.tip = None


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


class BlackOilGame:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Black Oil - Frontier Drilling")
        self.tile_size = 80
        self.scenario = SCENARIOS[0]
        self.day = 1
        self.cash = self.scenario.starting_cash
        self.price = random.randint(self.scenario.price_min, self.scenario.price_max)
        self.event_message = ""
        self.news_message = ""
        self.tiles: list[Tile] = []
        self.competitors: list[Competitor] = []
        self.selected_tile: Tile | None = None
        self.loan_balance = 0
        self.loan_limit = DEFAULT_LOAN_LIMIT
        self.loan_rate = DEFAULT_LOAN_RATE
        self.sound_enabled = True
        self.tooltips_enabled = True
        self.tooltips: list[Tooltip] = []
        self.research_level = 0
        self.petrol_price = random.randint(PETROL_PRICE_MIN, PETROL_PRICE_MAX)
        self.petrol_storage = 0
        self.contracts: list[Contract] = []
        self.refinery = Refinery()
        self.map_seed = random.randint(1000, 9999)
        self.decorations: list[tuple[int, int, int, str]] = []

        self._build_ui()
        self._new_game()

    def _build_ui(self) -> None:
        self.root.geometry("1120x670")
        self.root.resizable(False, False)

        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Game", command=self._new_game)
        file_menu.add_command(label="Save Game", command=self.save_game)
        file_menu.add_command(label="Load Game", command=self.load_game)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="Toggle Sound", command=self.toggle_sound)
        options_menu.add_command(label="Toggle Tooltips", command=self.toggle_tooltips)
        menubar.add_cascade(label="Options", menu=options_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

        main_frame = tk.Frame(self.root, bg="#0b1120")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            main_frame,
            width=620,
            height=620,
            bg="#0b1120",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, padx=16, pady=16)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        panel = tk.Frame(main_frame, width=400, bg="#0b1120")
        panel.grid(row=0, column=1, sticky="n", padx=(0, 16), pady=16)

        header = tk.Frame(panel, bg="#0b1120")
        header.pack(anchor="w")

        title = tk.Label(
            header,
            text="BLACK OIL",
            fg="#f8fafc",
            bg="#0b1120",
            font=("Helvetica", 20, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = tk.Label(
            header,
            text="Frontier Drilling Syndicate",
            fg="#94a3b8",
            bg="#0b1120",
            font=("Helvetica", 10, "italic"),
        )
        subtitle.grid(row=1, column=0, sticky="w")

        self.scenario_var = tk.StringVar(value=self.scenario.name)
        scenario_frame = tk.Frame(panel, bg="#0b1120")
        scenario_frame.pack(anchor="w", pady=(10, 6), fill="x")

        tk.Label(
            scenario_frame,
            text="Scenario",
            fg="#cbd5f5",
            bg="#0b1120",
            font=("Helvetica", 10, "bold"),
        ).grid(row=0, column=0, sticky="w")

        scenario_menu = ttk.Combobox(
            scenario_frame,
            textvariable=self.scenario_var,
            values=[scenario.name for scenario in SCENARIOS],
            state="readonly",
            width=22,
        )
        scenario_menu.grid(row=1, column=0, sticky="w")

        self.new_game_button = tk.Button(
            scenario_frame, text="New Game", command=self._new_game, bg="#1f2937", fg="#f8fafc"
        )
        self.new_game_button.grid(row=1, column=1, padx=8)

        self.scenario_desc = tk.Label(
            panel,
            text="",
            wraplength=320,
            justify="left",
            fg="#cbd5f5",
            bg="#0b1120",
            font=("Helvetica", 9),
        )
        self.scenario_desc.pack(anchor="w", pady=(4, 8))

        self.stats_label = tk.Label(
            panel,
            text="",
            justify="left",
            fg="#e2e8f0",
            bg="#0b1120",
            font=("Helvetica", 12),
        )
        self.stats_label.pack(anchor="w", pady=(6, 4))

        self.progress = ttk.Progressbar(panel, length=260, mode="determinate")
        self.progress.pack(anchor="w", pady=(2, 8))

        self.tile_label = tk.Label(
            panel,
            text="",
            justify="left",
            fg="#e2e8f0",
            bg="#0b1120",
            font=("Helvetica", 10),
        )
        self.tile_label.pack(anchor="w", pady=(6, 8))

        action_frame = tk.Frame(panel, bg="#0b1120")
        action_frame.pack(anchor="w")

        self.buy_button = tk.Button(action_frame, text="Buy Land", command=self.buy_land, width=20)
        self.buy_button.grid(row=0, column=0, pady=2)

        self.survey_button = tk.Button(action_frame, text="Survey", command=self.survey_tile, width=20)
        self.survey_button.grid(row=1, column=0, pady=2)

        self.drill_button = tk.Button(action_frame, text="Drill Well", command=self.drill_well, width=20)
        self.drill_button.grid(row=2, column=0, pady=2)

        self.pump_button = tk.Button(action_frame, text="Build Pump", command=self.build_pump, width=20)
        self.pump_button.grid(row=3, column=0, pady=2)

        self.upgrade_button = tk.Button(
            action_frame, text="Upgrade Pump", command=self.upgrade_pump, width=20
        )
        self.upgrade_button.grid(row=4, column=0, pady=2)

        self.storage_button = tk.Button(action_frame, text="Add Storage", command=self.add_storage, width=20)
        self.storage_button.grid(row=5, column=0, pady=2)

        self.refinery_button = tk.Button(
            action_frame, text="Build Refinery", command=self.build_refinery, width=20
        )
        self.refinery_button.grid(row=6, column=0, pady=2)

        self.upgrade_refinery_button = tk.Button(
            action_frame, text="Upgrade Refinery", command=self.upgrade_refinery, width=20
        )
        self.upgrade_refinery_button.grid(row=7, column=0, pady=2)

        self.research_button = tk.Button(
            action_frame, text="Research Efficiency", command=self.research_upgrade, width=20
        )
        self.research_button.grid(row=8, column=0, pady=2)

        self.sell_button = tk.Button(action_frame, text="Sell Oil", command=self.sell_oil, width=20)
        self.sell_button.grid(row=9, column=0, pady=2)

        self.sell_petrol_button = tk.Button(
            action_frame, text="Sell Petrol", command=self.sell_petrol, width=20
        )
        self.sell_petrol_button.grid(row=10, column=0, pady=2)

        self.contract_button = tk.Button(
            action_frame, text="Contracts", command=self.manage_contracts, width=20
        )
        self.contract_button.grid(row=11, column=0, pady=2)

        self.next_day_button = tk.Button(panel, text="Advance Day", command=self.next_day, width=20)
        self.next_day_button.pack(anchor="w", pady=(10, 4))

        loan_frame = tk.Frame(panel, bg="#0b1120")
        loan_frame.pack(anchor="w", pady=(2, 8))

        self.loan_button = tk.Button(loan_frame, text="Take Loan", command=self.take_loan, width=9)
        self.loan_button.grid(row=0, column=0, padx=(0, 6))

        self.repay_button = tk.Button(loan_frame, text="Repay Loan", command=self.repay_loan, width=9)
        self.repay_button.grid(row=0, column=1)

        save_load_frame = tk.Frame(panel, bg="#0b1120")
        save_load_frame.pack(anchor="w", pady=(2, 8))

        self.save_button = tk.Button(save_load_frame, text="Save Game", command=self.save_game, width=9)
        self.save_button.grid(row=0, column=0, padx=(0, 6))

        self.load_button = tk.Button(save_load_frame, text="Load Game", command=self.load_game, width=9)
        self.load_button.grid(row=0, column=1)

        self.sound_button = tk.Button(
            panel, text="Sound: On", command=self.toggle_sound, width=20, bg="#1f2937", fg="#f8fafc"
        )
        self.sound_button.pack(anchor="w", pady=(2, 8))

        self.competitor_label = tk.Label(
            panel,
            text="",
            justify="left",
            fg="#f8fafc",
            bg="#0b1120",
            font=("Helvetica", 10, "bold"),
        )
        self.competitor_label.pack(anchor="w", pady=(6, 2))

        self.contract_label = tk.Label(
            panel,
            text="",
            justify="left",
            fg="#e2e8f0",
            bg="#0b1120",
            font=("Helvetica", 9),
        )
        self.contract_label.pack(anchor="w", pady=(4, 2))

        self.news_label = tk.Label(
            panel,
            text="",
            justify="left",
            wraplength=320,
            fg="#fbbf24",
            bg="#0b1120",
            font=("Helvetica", 9, "italic"),
        )
        self.news_label.pack(anchor="w", pady=(4, 6))

        self.log = tk.Text(panel, width=42, height=12, state=tk.DISABLED, font=("Helvetica", 9))
        self.log.pack(anchor="w")

        self._install_tooltips()

    def _install_tooltips(self) -> None:
        self.tooltips.clear()
        tooltip_map = {
            self.buy_button: "Purchase unowned land tiles.",
            self.survey_button: "Estimate oil reserves before drilling.",
            self.drill_button: "Drill the selected tile for oil.",
            self.pump_button: "Install a pump to start production.",
            self.upgrade_button: "Upgrade pump output for higher yield.",
            self.storage_button: "Expand storage capacity on this tile.",
            self.refinery_button: "Build a refinery to convert oil into petrol.",
            self.upgrade_refinery_button: "Increase refinery capacity.",
            self.research_button: "Improve efficiency and reduce upkeep.",
            self.sell_button: "Sell all stored oil at market price.",
            self.sell_petrol_button: "Sell refined petrol at market price.",
            self.contract_button: "Review and sign delivery contracts.",
            self.next_day_button: "Advance to the next day.",
            self.loan_button: "Borrow cash, pay interest daily.",
            self.repay_button: "Repay part of your loan balance.",
            self.save_button: "Save the current game to a file.",
            self.load_button: "Load a saved game.",
        }
        if self.tooltips_enabled:
            for widget, text in tooltip_map.items():
                self.tooltips.append(Tooltip(widget, text))

    def _new_game(self) -> None:
        scenario_name = self.scenario_var.get()
        self.scenario = next(s for s in SCENARIOS if s.name == scenario_name)
        self.day = 1
        self.cash = self.scenario.starting_cash
        self.price = random.randint(self.scenario.price_min, self.scenario.price_max)
        self.event_message = ""
        self.news_message = ""
        self.loan_balance = 0
        self.loan_limit = DEFAULT_LOAN_LIMIT
        self.loan_rate = DEFAULT_LOAN_RATE
        self.research_level = 0
        self.petrol_price = random.randint(PETROL_PRICE_MIN, PETROL_PRICE_MAX)
        self.petrol_storage = 0
        self.contracts = []
        self.refinery = Refinery()
        self.map_seed = random.randint(1000, 9999)
        self.decorations = self._create_decorations(self.map_seed)
        self.tiles = self._create_tiles()
        self.competitors = self._create_competitors()
        self.selected_tile = None
        self._reset_log()
        self._install_tooltips()
        self._log("New game started.")
        self._refresh_ui()

    def _reset_log(self) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.config(state=tk.DISABLED)

    def _create_tiles(self) -> list[Tile]:
        tiles = []
        for row in range(self.scenario.grid_size):
            for col in range(self.scenario.grid_size):
                reserve = random.randint(0, 170)
                tiles.append(
                    Tile(
                        row=row,
                        col=col,
                        reserve=reserve,
                        output_rate=random.randint(OIL_PER_DAY_MIN, OIL_PER_DAY_MAX),
                    )
                )
        return tiles

    def _create_competitors(self) -> list[Competitor]:
        return [
            Competitor("Iron Ridge", 4200, 0.55, "#ef4444", 35),
            Competitor("Desert Drill", 3800, 0.45, "#f97316", 30),
            Competitor("Silver Creek", 3400, 0.4, "#a855f7", 28),
        ]

    def _create_decorations(self, seed: int) -> list[tuple[int, int, int, str]]:
        rng = random.Random(seed)
        decorations = []
        grid = self.scenario.grid_size
        for _ in range(grid * grid * 3):
            x = rng.randint(0, 599)
            y = rng.randint(0, 599)
            size = rng.randint(4, 12)
            color = rng.choice(["#0f172a", "#1e293b", "#334155", "#0f172a"])
            decorations.append((x, y, size, color))
        return decorations

    def _tile_at(self, x: int, y: int) -> Tile | None:
        col = x // self.tile_size
        row = y // self.tile_size
        for tile in self.tiles:
            if tile.row == row and tile.col == col:
                return tile
        return None

    def _owner_color(self, owner: str | None) -> str:
        if owner == "player":
            return "#15803d"
        for competitor in self.competitors:
            if competitor.name == owner:
                return competitor.color
        return "#1f2937"

    def _theme_palette(self) -> tuple[str, str, str]:
        if self.scenario.theme == "desert":
            return "#fde68a", "#f59e0b", "#92400e"
        if self.scenario.theme == "coastal":
            return "#93c5fd", "#38bdf8", "#0f766e"
        return "#a7f3d0", "#38bdf8", "#1f2937"

    def _draw_background(self, canvas_size: int) -> None:
        sky, mid, ground = self._theme_palette()
        step = max(8, canvas_size // 30)
        for i in range(0, canvas_size, step):
            ratio = i / canvas_size
            if ratio < 0.6:
                color = sky if i % (step * 2) == 0 else mid
            else:
                color = ground
            self.canvas.create_rectangle(0, i, canvas_size, i + step, fill=color, outline="")

        sun_size = canvas_size * 0.18
        self.canvas.create_oval(
            canvas_size * 0.68,
            canvas_size * 0.08,
            canvas_size * 0.68 + sun_size,
            canvas_size * 0.08 + sun_size,
            fill="#fde047",
            outline="",
        )

        cloud_color = "#e2e8f0"
        for i in range(3):
            x = canvas_size * (0.12 + i * 0.2)
            y = canvas_size * (0.12 + i * 0.05)
            self.canvas.create_oval(x, y, x + 50, y + 25, fill=cloud_color, outline="")
            self.canvas.create_oval(x + 20, y - 10, x + 60, y + 20, fill=cloud_color, outline="")
            self.canvas.create_oval(x + 40, y, x + 80, y + 28, fill=cloud_color, outline="")

        for x, y, size, color in self.decorations:
            self.canvas.create_oval(x, y, x + size, y + size, fill=color, outline="")

    def _draw_pump(self, x0: int, y0: int, size: int, color: str) -> None:
        base = size * 0.2
        self.canvas.create_rectangle(
            x0 + base,
            y0 + size * 0.6,
            x0 + size - base,
            y0 + size * 0.75,
            fill=color,
            outline="",
        )
        self.canvas.create_line(
            x0 + size * 0.3,
            y0 + size * 0.6,
            x0 + size * 0.5,
            y0 + size * 0.3,
            fill=color,
            width=3,
        )
        self.canvas.create_line(
            x0 + size * 0.5,
            y0 + size * 0.3,
            x0 + size * 0.7,
            y0 + size * 0.6,
            fill=color,
            width=3,
        )
        self.canvas.create_oval(
            x0 + size * 0.46,
            y0 + size * 0.2,
            x0 + size * 0.54,
            y0 + size * 0.28,
            fill=color,
            outline="",
        )

    def _draw_rig(self, x0: int, y0: int, size: int, color: str) -> None:
        self.canvas.create_polygon(
            x0 + size * 0.2,
            y0 + size * 0.8,
            x0 + size * 0.5,
            y0 + size * 0.2,
            x0 + size * 0.8,
            y0 + size * 0.8,
            fill="",
            outline=color,
            width=2,
        )
        self.canvas.create_line(
            x0 + size * 0.35,
            y0 + size * 0.65,
            x0 + size * 0.65,
            y0 + size * 0.65,
            fill=color,
            width=2,
        )
        self.canvas.create_line(
            x0 + size * 0.45,
            y0 + size * 0.45,
            x0 + size * 0.55,
            y0 + size * 0.45,
            fill=color,
            width=2,
        )

    def _draw_storage_tank(self, x0: int, y0: int, size: int, color: str) -> None:
        self.canvas.create_oval(
            x0 + size * 0.2,
            y0 + size * 0.15,
            x0 + size * 0.8,
            y0 + size * 0.35,
            fill=color,
            outline="",
        )
        self.canvas.create_rectangle(
            x0 + size * 0.2,
            y0 + size * 0.25,
            x0 + size * 0.8,
            y0 + size * 0.75,
            fill=color,
            outline="",
        )
        self.canvas.create_oval(
            x0 + size * 0.2,
            y0 + size * 0.65,
            x0 + size * 0.8,
            y0 + size * 0.85,
            fill=color,
            outline="",
        )

    def _draw_pipeline(self, tile: Tile, size: int) -> None:
        if tile.owner != "player" or not tile.has_pump:
            return
        x0 = tile.col * size
        y0 = tile.row * size
        x1 = x0 + size
        y1 = y0 + size
        self.canvas.create_line(
            x0 + size * 0.1,
            y1 - size * 0.2,
            x1 - size * 0.1,
            y1 - size * 0.2,
            fill="#0ea5e9",
            width=3,
        )
        self.canvas.create_oval(
            x1 - size * 0.16,
            y1 - size * 0.28,
            x1 - size * 0.06,
            y1 - size * 0.18,
            fill="#0ea5e9",
            outline="",
        )

    def _draw_grid(self) -> None:
        self.canvas.delete("all")
        grid_size = self.scenario.grid_size
        self.tile_size = min(600 // grid_size, 110)
        canvas_size = self.tile_size * grid_size
        self.canvas.config(width=canvas_size, height=canvas_size)
        self._draw_background(canvas_size)

        for tile in self.tiles:
            x0 = tile.col * self.tile_size
            y0 = tile.row * self.tile_size
            x1 = x0 + self.tile_size
            y1 = y0 + self.tile_size
            fill = self._owner_color(tile.owner)
            outline = "#334155"
            if tile.depleted and tile.owner:
                fill = "#475569"

            self.canvas.create_rectangle(
                x0 + 3,
                y0 + 4,
                x1 + 3,
                y1 + 4,
                fill="#0f172a",
                outline="",
            )
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=2)
            self.canvas.create_rectangle(
                x0 + 4,
                y0 + 4,
                x1 - 4,
                y1 - 4,
                outline="#94a3b8",
                width=1,
            )

            if tile.drilled:
                self.canvas.create_oval(
                    x0 + 8,
                    y0 + 8,
                    x0 + 26,
                    y0 + 26,
                    fill="#fbbf24",
                    outline="",
                )

            if tile.has_pump:
                self._draw_pump(x0 + 8, y0 + 18, self.tile_size - 16, "#e2e8f0")

            if tile.owner == "player":
                storage_ratio = tile.storage / tile.capacity if tile.capacity else 0
                bar_height = int(self.tile_size * storage_ratio)
                self.canvas.create_rectangle(
                    x1 - 12,
                    y1 - bar_height,
                    x1 - 4,
                    y1,
                    fill="#38bdf8",
                    outline="",
                )

            if tile.owner == "player" and tile.drilled:
                self._draw_rig(x0 + 6, y0 + 12, self.tile_size - 12, "#f8fafc")
            if tile.owner == "player" and tile.capacity > 20:
                self._draw_storage_tank(x0 + 6, y0 + self.tile_size * 0.58, self.tile_size - 12, "#e2e8f0")

            if tile is self.selected_tile:
                self.canvas.create_rectangle(
                    x0 + 3,
                    y0 + 3,
                    x1 - 3,
                    y1 - 3,
                    outline="#fbbf24",
                    width=3,
                )

            if tile.owner:
                label = tile.owner if tile.owner == "player" else "Rival"
                self.canvas.create_text(
                    x0 + self.tile_size / 2,
                    y1 - 10,
                    text=label,
                    fill="#f8fafc",
                    font=("Helvetica", 8, "bold"),
                )

            if tile.owner == "player" and tile.has_pump:
                self.canvas.create_text(
                    x0 + self.tile_size / 2,
                    y0 + 12,
                    text=f"L{tile.pump_level}",
                    fill="#f8fafc",
                    font=("Helvetica", 7, "bold"),
                )

        for tile in self.tiles:
            self._draw_pipeline(tile, self.tile_size)

    def _update_buttons(self) -> None:
        tile = self.selected_tile
        has_tile = tile is not None
        is_player_tile = tile is not None and tile.owner == "player"
        self.buy_button.config(state=tk.NORMAL if has_tile and tile and tile.owner is None else tk.DISABLED)
        self.survey_button.config(state=tk.NORMAL if has_tile and is_player_tile else tk.DISABLED)
        self.drill_button.config(
            state=tk.NORMAL if has_tile and is_player_tile and not tile.drilled else tk.DISABLED
        )
        self.pump_button.config(
            state=tk.NORMAL
            if has_tile and is_player_tile and tile.drilled and not tile.has_pump and not tile.depleted
            else tk.DISABLED
        )
        self.upgrade_button.config(
            state=tk.NORMAL
            if has_tile and is_player_tile and tile.has_pump and tile.pump_level < MAX_PUMP_LEVEL
            else tk.DISABLED
        )
        self.storage_button.config(state=tk.NORMAL if has_tile and is_player_tile else tk.DISABLED)
        self.refinery_button.config(
            state=tk.NORMAL if self.refinery.level == 0 else tk.DISABLED
        )
        self.upgrade_refinery_button.config(
            state=tk.NORMAL if self.refinery.active else tk.DISABLED
        )
        self.research_button.config(state=tk.NORMAL if self.cash >= RESEARCH_COST else tk.DISABLED)
        self.sell_button.config(state=tk.NORMAL if self._total_storage("player") > 0 else tk.DISABLED)
        self.sell_petrol_button.config(state=tk.NORMAL if self.petrol_storage > 0 else tk.DISABLED)

    def _refresh_ui(self) -> None:
        self.stats_label.config(
            text=(
                f"Scenario: {self.scenario.name}\n"
                f"Day: {self.day}/{self.scenario.max_days}\n"
                f"Cash: ${self.cash:,}\n"
                f"Oil Price: ${self.price}/barrel\n"
                f"Petrol Price: ${self.petrol_price}/barrel\n"
                f"Stored Oil: {self._total_storage('player')} barrels\n"
                f"Stored Petrol: {self.petrol_storage} barrels\n"
                f"Refinery: {'Online' if self.refinery.active else 'Offline'} "
                f"(Cap {self.refinery.capacity})\n"
                f"Research Level: {self.research_level}\n"
                f"Loan Balance: ${self.loan_balance:,}\n"
                f"Event: {self.event_message or 'None'}"
            )
        )
        self.scenario_desc.config(text=self.scenario.description)
        self.progress["value"] = (self.day / self.scenario.max_days) * 100

        if self.selected_tile:
            tile = self.selected_tile
            reserve_text = "Unknown" if not tile.drilled else max(tile.reserve, 0)
            survey_text = "None"
            if tile.survey_low is not None and tile.survey_high is not None:
                survey_text = f"{tile.survey_low}-{tile.survey_high}"
            pump_text = f"Level {tile.pump_level}" if tile.has_pump else "None"
            self.tile_label.config(
                text=(
                    f"Selected Tile ({tile.row + 1}, {tile.col + 1})\n"
                    f"Owner: {tile.owner or 'Unowned'}\n"
                    f"Survey: {survey_text}\n"
                    f"Drilled: {'Yes' if tile.drilled else 'No'}\n"
                    f"Pump: {pump_text}\n"
                    f"Reserve: {reserve_text}\n"
                    f"Storage: {tile.storage}/{tile.capacity} barrels"
                )
            )
        else:
            self.tile_label.config(text="Select a tile to inspect.")

        self.news_label.config(text=self.news_message)
        self._draw_grid()
        self._update_buttons()
        self._update_competitor_panel()

    def _update_competitor_panel(self) -> None:
        lines = ["Competitors:"]
        for competitor in self.competitors:
            lines.append(f"- {competitor.name}: ${competitor.cash:,}")
        self.competitor_label.config(text="\n".join(lines))

        if not self.contracts:
            self.contract_label.config(text="Contracts: None")
        else:
            contract_lines = ["Contracts:"]
            for contract in self.contracts:
                contract_lines.append(
                    f"- {contract.name}: {contract.delivered}/{contract.volume} "
                    f"({contract.days_remaining}d)"
                )
            self.contract_label.config(text="\n".join(contract_lines))

    def _log(self, message: str) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _play_sound(self, action: str) -> None:
        if not self.sound_enabled:
            return
        if action in {"buy", "sell", "loan"}:
            self.root.bell()
        elif action in {"error"}:
            self.root.bell()
            self.root.bell()
        else:
            self.root.bell()

    def toggle_sound(self) -> None:
        self.sound_enabled = not self.sound_enabled
        label = "On" if self.sound_enabled else "Off"
        self.sound_button.config(text=f"Sound: {label}")
        self._log(f"Sound effects turned {label.lower()}.")

    def toggle_tooltips(self) -> None:
        self.tooltips_enabled = not self.tooltips_enabled
        if self.tooltips_enabled:
            self._install_tooltips()
            self._log("Tooltips enabled.")
        else:
            for tip in self.tooltips:
                tip._hide(None)
            self.tooltips.clear()
            self._log("Tooltips disabled.")

    def show_about(self) -> None:
        messagebox.showinfo(
            "About Black Oil",
            "Black Oil - Frontier Drilling\n"
            "A strategy prototype inspired by classic oil boom simulations.\n"
            "Manage wells, refineries, contracts, and market swings.",
        )

    def _on_canvas_click(self, event: tk.Event) -> None:
        tile = self._tile_at(event.x, event.y)
        if tile:
            self.selected_tile = tile
            self._refresh_ui()

    def _total_storage(self, owner: str) -> int:
        return sum(tile.storage for tile in self.tiles if tile.owner == owner)

    def _owned_tiles(self, owner: str) -> list[Tile]:
        return [tile for tile in self.tiles if tile.owner == owner]

    def buy_land(self) -> None:
        if not self.selected_tile:
            return
        tile = self.selected_tile
        if tile.owner is not None:
            return
        if self.cash < self.scenario.land_cost:
            messagebox.showinfo("Insufficient Cash", "You need more cash to buy this land.")
            self._play_sound("error")
            return
        tile.owner = "player"
        self.cash -= self.scenario.land_cost
        self._log(f"Bought land at ({tile.row + 1}, {tile.col + 1}) for ${self.scenario.land_cost}.")
        self._play_sound("buy")
        self._refresh_ui()

    def survey_tile(self) -> None:
        if not self.selected_tile:
            return
        tile = self.selected_tile
        if tile.owner != "player":
            return
        if self.cash < SURVEY_COST:
            messagebox.showinfo("Insufficient Cash", "You need more cash to run a survey.")
            self._play_sound("error")
            return
        self.cash -= SURVEY_COST
        if tile.reserve <= 0:
            low, high = 0, 10
        else:
            error = random.uniform(0.15, 0.35)
            low = max(0, int(tile.reserve * (1 - error)))
            high = int(tile.reserve * (1 + error))
        tile.survey_low = low
        tile.survey_high = high
        self._log(f"Survey complete for ({tile.row + 1}, {tile.col + 1}).")
        self._play_sound("survey")
        self._refresh_ui()

    def drill_well(self) -> None:
        if not self.selected_tile:
            return
        tile = self.selected_tile
        if tile.owner != "player":
            return
        if self.cash < self.scenario.drill_cost:
            messagebox.showinfo("Insufficient Cash", "You need more cash to drill here.")
            self._play_sound("error")
            return
        tile.drilled = True
        self.cash -= self.scenario.drill_cost
        if tile.reserve <= 0:
            self._log("Dry well! No oil in this tile.")
        else:
            self._log(f"Drilled well. Estimated reserves: {tile.reserve} barrels.")
        self._play_sound("drill")
        self._refresh_ui()

    def build_pump(self) -> None:
        if not self.selected_tile:
            return
        tile = self.selected_tile
        if tile.owner != "player":
            return
        if self.cash < self.scenario.pump_cost:
            messagebox.showinfo("Insufficient Cash", "You need more cash to build a pump.")
            self._play_sound("error")
            return
        tile.pump_level = 1
        self.cash -= self.scenario.pump_cost
        self._log("Pump installed. Production will start next day.")
        self._play_sound("build")
        self._refresh_ui()

    def upgrade_pump(self) -> None:
        if not self.selected_tile:
            return
        tile = self.selected_tile
        if tile.owner != "player" or not tile.has_pump:
            return
        if tile.pump_level >= MAX_PUMP_LEVEL:
            return
        if self.cash < PUMP_UPGRADE_COST:
            messagebox.showinfo("Insufficient Cash", "You need more cash to upgrade the pump.")
            self._play_sound("error")
            return
        tile.pump_level += 1
        self.cash -= PUMP_UPGRADE_COST
        self._log(f"Pump upgraded to level {tile.pump_level}.")
        self._play_sound("upgrade")
        self._refresh_ui()

    def add_storage(self) -> None:
        if not self.selected_tile:
            return
        tile = self.selected_tile
        if tile.owner != "player":
            return
        if self.cash < self.scenario.storage_cost:
            messagebox.showinfo("Insufficient Cash", "You need more cash to expand storage.")
            self._play_sound("error")
            return
        tile.capacity += STORAGE_EXPANSION
        self.cash -= self.scenario.storage_cost
        self._log(f"Added storage on tile ({tile.row + 1}, {tile.col + 1}).")
        self._play_sound("build")
        self._refresh_ui()

    def build_refinery(self) -> None:
        if self.refinery.active:
            return
        if self.cash < REFINERY_BUILD_COST:
            messagebox.showinfo("Insufficient Cash", "You need more cash to build a refinery.")
            self._play_sound("error")
            return
        self.cash -= REFINERY_BUILD_COST
        self.refinery.level = 1
        self.refinery.capacity = REFINERY_BASE_CAPACITY
        self._log("Refinery built. You can now refine oil into petrol.")
        self._play_sound("build")
        self._refresh_ui()

    def upgrade_refinery(self) -> None:
        if not self.refinery.active:
            return
        if self.cash < REFINERY_UPGRADE_COST:
            messagebox.showinfo("Insufficient Cash", "You need more cash to upgrade the refinery.")
            self._play_sound("error")
            return
        self.cash -= REFINERY_UPGRADE_COST
        self.refinery.level += 1
        self.refinery.capacity += int(REFINERY_BASE_CAPACITY * 0.6)
        self._log(f"Refinery upgraded to level {self.refinery.level}.")
        self._play_sound("upgrade")
        self._refresh_ui()

    def research_upgrade(self) -> None:
        if self.cash < RESEARCH_COST:
            messagebox.showinfo("Insufficient Cash", "You need more cash to fund research.")
            self._play_sound("error")
            return
        self.cash -= RESEARCH_COST
        self.research_level += 1
        self._log("Research complete. Efficiency improved.")
        self._play_sound("upgrade")
        self._refresh_ui()

    def manage_contracts(self) -> None:
        offers = self._generate_contract_offers()
        lines = ["Available Contracts:"]
        for idx, offer in enumerate(offers, start=1):
            lines.append(
                f"{idx}. {offer.name} - {offer.volume} barrels @ ${offer.price} "
                f"({offer.days_remaining} days)"
            )
        lines.append("Enter contract number to accept (0 to cancel).")
        choice = simpledialog.askinteger("Contracts", "\n".join(lines), minvalue=0, maxvalue=len(offers))
        if choice is None or choice == 0:
            return
        contract = offers[choice - 1]
        self.contracts.append(contract)
        self._log(f"Signed contract: {contract.name} for {contract.volume} barrels.")
        self._play_sound("buy")
        self._refresh_ui()

    def _generate_contract_offers(self) -> list[Contract]:
        offers = []
        base_volume = random.randint(60, 140)
        for _ in range(3):
            volume = base_volume + random.randint(-20, 40)
            price = max(self.price + random.randint(-5, 25), self.scenario.price_min)
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

    def sell_petrol(self) -> None:
        if self.petrol_storage <= 0:
            return
        revenue = self.petrol_storage * self.petrol_price
        self.cash += revenue
        self._log(f"Sold {self.petrol_storage} barrels of petrol for ${revenue}.")
        self.petrol_storage = 0
        self._play_sound("sell")
        self._refresh_ui()

    def sell_oil(self) -> None:
        total_storage = self._total_storage("player")
        if total_storage <= 0:
            return
        revenue = total_storage * self.price
        self.cash += revenue
        for tile in self._owned_tiles("player"):
            tile.storage = 0
        self._log(f"Sold {total_storage} barrels for ${revenue}.")
        self._play_sound("sell")
        self._refresh_ui()

    def take_loan(self) -> None:
        if self.loan_balance >= self.loan_limit:
            messagebox.showinfo("Loan Limit", "You have reached the loan limit.")
            self._play_sound("error")
            return
        amount = min(LOAN_CHUNK, self.loan_limit - self.loan_balance)
        self.cash += amount
        self.loan_balance += amount
        self._log(f"Took a loan for ${amount}.")
        self._play_sound("loan")
        self._refresh_ui()

    def repay_loan(self) -> None:
        if self.loan_balance <= 0:
            return
        amount = min(LOAN_CHUNK, self.loan_balance)
        if self.cash < amount:
            messagebox.showinfo("Insufficient Cash", "You need more cash to repay the loan.")
            self._play_sound("error")
            return
        self.cash -= amount
        self.loan_balance -= amount
        self._log(f"Repaid ${amount} of loans.")
        self._play_sound("loan")
        self._refresh_ui()

    def next_day(self) -> None:
        if self.day >= self.scenario.max_days:
            self._final_score()
            return

        self.day += 1
        self._play_sound("advance")
        self._apply_market()
        self._apply_petrol_market()
        self._produce_oil()
        self._refine_oil()
        self._process_contracts()
        self._competitor_turns()
        self._random_event()
        self._daily_maintenance()
        self._apply_interest()
        self._refresh_news()
        self._refresh_ui()

        if self.day == self.scenario.max_days:
            self._final_score()

    def _apply_market(self) -> None:
        delta = random.randint(-20, 20)
        self.price = max(self.scenario.price_min, min(self.scenario.price_max, self.price + delta))

    def _apply_petrol_market(self) -> None:
        delta = random.randint(-18, 18)
        self.petrol_price = max(PETROL_PRICE_MIN, min(PETROL_PRICE_MAX, self.petrol_price + delta))

    def _produce_oil(self) -> None:
        for tile in self.tiles:
            if tile.has_pump and tile.reserve > 0 and tile.available_capacity > 0:
                efficiency_bonus = 1 + (self.research_level * 0.05)
                output = int(tile.current_output * efficiency_bonus)
                output = min(output, tile.reserve, tile.available_capacity)
                tile.reserve -= output
                tile.storage += output
                if tile.reserve == 0:
                    self._log(
                        f"Well at ({tile.row + 1}, {tile.col + 1}) ran dry. Storage holds {tile.storage} barrels."
                    )

    def _refine_oil(self) -> None:
        if not self.refinery.active:
            return
        available_oil = self._total_storage("player")
        if available_oil <= 0:
            return
        capacity = self.refinery.capacity
        refine_amount = min(available_oil, capacity)
        self._withdraw_oil(refine_amount)
        self.petrol_storage += refine_amount
        self._log(f"Refined {refine_amount} barrels into petrol.")

    def _withdraw_oil(self, amount: int) -> None:
        remaining = amount
        for tile in self._owned_tiles("player"):
            if remaining <= 0:
                break
            if tile.storage <= remaining:
                remaining -= tile.storage
                tile.storage = 0
            else:
                tile.storage -= remaining
                remaining = 0

    def _competitor_turns(self) -> None:
        for competitor in self.competitors:
            if competitor.will_expand():
                self._competitor_expand(competitor)
            self._competitor_operate(competitor)

    def _competitor_expand(self, competitor: Competitor) -> None:
        open_tiles = [tile for tile in self.tiles if tile.owner is None]
        if not open_tiles or competitor.cash < self.scenario.land_cost:
            return
        target = random.choice(open_tiles)
        target.owner = competitor.name
        competitor.cash -= self.scenario.land_cost
        self._log(f"{competitor.name} secured land at ({target.row + 1}, {target.col + 1}).")

    def _competitor_operate(self, competitor: Competitor) -> None:
        for tile in self._owned_tiles(competitor.name):
            if not tile.drilled and competitor.cash >= self.scenario.drill_cost:
                tile.drilled = True
                competitor.cash -= self.scenario.drill_cost
            if tile.drilled and not tile.has_pump and competitor.cash >= self.scenario.pump_cost and tile.reserve > 0:
                tile.pump_level = 1
                competitor.cash -= self.scenario.pump_cost
            if tile.has_pump and tile.pump_level < MAX_PUMP_LEVEL and competitor.cash >= PUMP_UPGRADE_COST:
                tile.pump_level += 1
                competitor.cash -= PUMP_UPGRADE_COST
            if tile.has_pump and tile.available_capacity < 5 and competitor.cash >= self.scenario.storage_cost:
                tile.capacity += 10
                competitor.cash -= self.scenario.storage_cost

        storage = sum(tile.storage for tile in self._owned_tiles(competitor.name))
        if storage >= competitor.storage_threshold or self.price > self.scenario.price_max * 0.85:
            revenue = storage * self.price
            competitor.cash += revenue
            for tile in self._owned_tiles(competitor.name):
                tile.storage = 0
            if storage > 0:
                self._log(f"{competitor.name} sold {storage} barrels for ${revenue}.")

    def _process_contracts(self) -> None:
        if not self.contracts:
            return
        for contract in list(self.contracts):
            deliverable = min(contract.remaining, self._total_storage("player"))
            if deliverable > 0:
                self._withdraw_oil(deliverable)
                contract.delivered += deliverable
                revenue = deliverable * contract.price
                self.cash += revenue
                self._log(f"Delivered {deliverable} barrels to {contract.name} for ${revenue}.")
            contract.days_remaining -= 1
            if contract.days_remaining <= 0:
                if contract.remaining > 0:
                    self.cash = max(0, self.cash - CONTRACT_PENALTY)
                    self._log(f"Missed contract with {contract.name}. Penalty: ${CONTRACT_PENALTY}.")
                self.contracts.remove(contract)

    def _daily_maintenance(self) -> None:
        pump_count = sum(1 for tile in self._owned_tiles("player") if tile.has_pump)
        refinery_cost = MAINTENANCE_COST if self.refinery.active else 0
        base = MAINTENANCE_COST + refinery_cost + pump_count * 15
        efficiency = 1 - min(0.3, self.research_level * 0.03)
        cost = int(base * efficiency)
        if cost > 0:
            self.cash = max(0, self.cash - cost)
            self._log(f"Maintenance costs: ${cost}.")

    def _random_event(self) -> None:
        self.event_message = ""
        if random.random() > self.scenario.event_chance:
            return
        roll = random.random()
        if roll < 0.35:
            loss = random.randint(150, 450)
            self.cash = max(0, self.cash - loss)
            self.event_message = f"Equipment repairs cost ${loss}."
        elif roll < 0.65:
            bonus = random.randint(120, 480)
            self.cash += bonus
            self.event_message = f"Pipeline bonus payout: ${bonus}."
        else:
            if self.price < self.scenario.price_max:
                self.price += 12
                self.event_message = "Rumors of shortage raise oil prices."
        if self.event_message:
            self._log(self.event_message)

    def _apply_interest(self) -> None:
        if self.loan_balance <= 0:
            return
        interest = int(self.loan_balance * self.loan_rate)
        self.loan_balance += interest
        self._log(f"Loan interest accrued: ${interest}.")

    def _refresh_news(self) -> None:
        headlines = [
            "Rail tycoon eyes new drilling leases.",
            "Steamship delays tighten coastal supply.",
            "Bankers whisper about a credit squeeze.",
            "Local boomtown celebrates new refinery.",
            "Sparks from the rail yard ignite rumors of expansion.",
            "Petrol demand spikes among motor carriage owners.",
            "Pipeline inspectors report new safety standards.",
            "Refinery guild offers bonuses for steady deliveries.",
        ]
        self.news_message = random.choice(headlines)

    def _final_score(self) -> None:
        assets = (
            self.cash
            + self._total_storage("player") * self.price
            + self.petrol_storage * self.petrol_price
            - self.loan_balance
        )
        messagebox.showinfo(
            "Season Over",
            f"You finished with ${assets:,} in assets.\n"
            "Thanks for playing Black Oil!",
        )

    def save_game(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Black Oil Save", "*.json")],
        )
        if not path:
            return
        data = {
            "scenario": self.scenario.name,
            "day": self.day,
            "cash": self.cash,
            "price": self.price,
            "event_message": self.event_message,
            "news_message": self.news_message,
            "loan_balance": self.loan_balance,
            "loan_limit": self.loan_limit,
            "loan_rate": self.loan_rate,
            "research_level": self.research_level,
            "petrol_price": self.petrol_price,
            "petrol_storage": self.petrol_storage,
            "refinery": {"level": self.refinery.level, "capacity": self.refinery.capacity},
            "contracts": [
                {
                    "name": contract.name,
                    "volume": contract.volume,
                    "price": contract.price,
                    "days_remaining": contract.days_remaining,
                    "delivered": contract.delivered,
                }
                for contract in self.contracts
            ],
            "map_seed": self.map_seed,
            "decorations": self.decorations,
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
                for tile in self.tiles
            ],
            "competitors": [
                {
                    "name": competitor.name,
                    "cash": competitor.cash,
                    "aggressiveness": competitor.aggressiveness,
                    "color": competitor.color,
                    "storage_threshold": competitor.storage_threshold,
                }
                for competitor in self.competitors
            ],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._log(f"Game saved to {path}.")
        self._play_sound("save")

    def load_game(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Black Oil Save", "*.json")])
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        scenario_name = data.get("scenario", SCENARIOS[0].name)
        self.scenario = next((s for s in SCENARIOS if s.name == scenario_name), SCENARIOS[0])
        self.scenario_var.set(self.scenario.name)
        self.day = data.get("day", 1)
        self.cash = data.get("cash", self.scenario.starting_cash)
        self.price = data.get("price", self.scenario.price_min)
        self.event_message = data.get("event_message", "")
        self.news_message = data.get("news_message", "")
        self.loan_balance = data.get("loan_balance", 0)
        self.loan_limit = data.get("loan_limit", DEFAULT_LOAN_LIMIT)
        self.loan_rate = data.get("loan_rate", DEFAULT_LOAN_RATE)
        self.research_level = data.get("research_level", 0)
        self.petrol_price = data.get("petrol_price", random.randint(PETROL_PRICE_MIN, PETROL_PRICE_MAX))
        self.petrol_storage = data.get("petrol_storage", 0)
        refinery_data = data.get("refinery", {})
        self.refinery = Refinery(
            level=refinery_data.get("level", 0),
            capacity=refinery_data.get("capacity", 0),
        )
        self.contracts = [
            Contract(
                name=item["name"],
                volume=item["volume"],
                price=item["price"],
                days_remaining=item["days_remaining"],
                delivered=item.get("delivered", 0),
            )
            for item in data.get("contracts", [])
        ]
        self.map_seed = data.get("map_seed", random.randint(1000, 9999))
        self.decorations = [tuple(item) for item in data.get("decorations", [])] or self._create_decorations(
            self.map_seed
        )

        self.tiles = [
            Tile(
                row=tile_data["row"],
                col=tile_data["col"],
                reserve=tile_data["reserve"],
                output_rate=tile_data["output_rate"],
                owner=tile_data.get("owner"),
                drilled=tile_data.get("drilled", False),
                pump_level=tile_data.get("pump_level", 0),
                storage=tile_data.get("storage", 0),
                capacity=tile_data.get("capacity", 20),
                survey_low=tile_data.get("survey_low"),
                survey_high=tile_data.get("survey_high"),
            )
            for tile_data in data.get("tiles", [])
        ]
        self.competitors = [
            Competitor(
                name=comp["name"],
                cash=comp["cash"],
                aggressiveness=comp["aggressiveness"],
                color=comp["color"],
                storage_threshold=comp.get("storage_threshold", 30),
            )
            for comp in data.get("competitors", [])
        ]
        if not self.tiles:
            self.tiles = self._create_tiles()
        if not self.competitors:
            self.competitors = self._create_competitors()
        self.selected_tile = None
        self._reset_log()
        self._log(f"Game loaded from {path}.")
        self._play_sound("load")
        self._refresh_ui()


def main() -> None:
    root = tk.Tk()
    BlackOilGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
