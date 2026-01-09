from __future__ import annotations

import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import economy
from .engine import ai, drilling, finance, leasing, market, production, projects
from .models import Buyer, Contract
from . import persistence
from .state import (
    HUB_MAX_LEVEL,
    LOAN_CHUNK,
    MAP_PIXEL_SIZE,
    MAX_PUMP_LEVEL,
    REFINERY_BASE_CAPACITY,
    REFINERY_BUILD_COST,
    REFINERY_UPGRADE_COST,
    REPUTATION_MAX,
    SCENARIOS,
    STORAGE_EXPANSION,
    SURVEY_COST,
    TRADE_MAX_VOLUME,
    TRADE_MIN_VOLUME,
    add_storage,
    apply_trade,
    build_hub,
    build_pump,
    build_refinery,
    buy_land,
    drill_well,
    new_game_state,
    repay_loan,
    research_upgrade,
    sell_oil,
    sell_petrol,
    sign_contract,
    survey_tile,
    take_loan,
    upgrade_hub,
    upgrade_pump,
    upgrade_refinery,
    GameState,
    PUMP_UPGRADE_COST,
    RESEARCH_COST,
    HUB_BUILD_COST,
    HUB_UPGRADE_COST,
)


class BlackOilApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Black Oil - Frontier Drilling")
        self.state = new_game_state(SCENARIOS[0])
        self.selected_tile = None
        self.fx_tick = 0
        self.fx_running = False

        self._build_ui()
        self._bind_shortcuts()
        self._refresh_ui()
        self._start_fx_loop()

    def _build_ui(self) -> None:
        self.root.geometry("1260x760")
        self.root.resizable(False, False)

        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Game", command=self.new_game)
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
        help_menu.add_command(label="Statistics", command=self.show_statistics)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

        main_frame = tk.Frame(self.root, bg="#0b1120")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            main_frame,
            width=MAP_PIXEL_SIZE,
            height=MAP_PIXEL_SIZE,
            bg="#0b1120",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, padx=16, pady=16)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        panel = tk.Frame(main_frame, width=420, bg="#0b1120")
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

        self.scenario_var = tk.StringVar(value=self.state.scenario.name)
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
            scenario_frame, text="New Game", command=self.new_game, bg="#1f2937", fg="#f8fafc"
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

        self.progress = ttk.Progressbar(panel, length=320, mode="determinate")
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

        self.hub_button = tk.Button(
            action_frame, text="Build Transport Hub", command=self.build_hub, width=20
        )
        self.hub_button.grid(row=9, column=0, pady=2)

        self.upgrade_hub_button = tk.Button(
            action_frame, text="Upgrade Transport Hub", command=self.upgrade_hub, width=20
        )
        self.upgrade_hub_button.grid(row=10, column=0, pady=2)

        self.trade_button = tk.Button(
            action_frame, text="Trade Market", command=self.trade_market, width=20
        )
        self.trade_button.grid(row=11, column=0, pady=2)

        self.sell_button = tk.Button(action_frame, text="Sell Oil", command=self.sell_oil, width=20)
        self.sell_button.grid(row=12, column=0, pady=2)

        self.sell_petrol_button = tk.Button(
            action_frame, text="Sell Petrol", command=self.sell_petrol, width=20
        )
        self.sell_petrol_button.grid(row=13, column=0, pady=2)

        self.contract_button = tk.Button(
            action_frame, text="Contracts", command=self.manage_contracts, width=20
        )
        self.contract_button.grid(row=14, column=0, pady=2)

        self.auto_refine_var = tk.BooleanVar(value=self.state.auto_refine)
        self.auto_refine_check = tk.Checkbutton(
            panel,
            text="Auto-refine",
            variable=self.auto_refine_var,
            command=self.toggle_auto_refine,
            fg="#e2e8f0",
            bg="#0b1120",
            selectcolor="#1f2937",
            activebackground="#0b1120",
            activeforeground="#f8fafc",
        )
        self.auto_refine_check.pack(anchor="w", pady=(6, 2))

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

        self.summary_label = tk.Label(
            panel,
            text="",
            justify="left",
            wraplength=320,
            fg="#e2e8f0",
            bg="#0b1120",
            font=("Helvetica", 9),
        )
        self.summary_label.pack(anchor="w", pady=(4, 6))

        self.log = tk.Text(panel, width=44, height=10, state=tk.DISABLED, font=("Helvetica", 9))
        self.log.pack(anchor="w")

    def _bind_shortcuts(self) -> None:
        self.root.bind("n", lambda _event: self.next_day())
        self.root.bind("s", lambda _event: self.save_game())
        self.root.bind("l", lambda _event: self.load_game())

    def _refresh_ui(self) -> None:
        self.stats_label.config(
            text=(
                f"Scenario: {self.state.scenario.name}\n"
                f"Day: {self.state.day}/{self.state.scenario.max_days}\n"
                f"Cash: ${self.state.cash:,}\n"
                f"Oil Price: ${self.state.price}/barrel\n"
                f"Petrol Price: ${self.state.petrol_price}/barrel\n"
                f"Stored Oil: {economy.total_storage(self.state, 'player')} barrels\n"
                f"Stored Petrol: {self.state.petrol_storage} barrels\n"
                f"Refinery: {'Online' if self.state.refinery.active else 'Offline'} "
                f"(Cap {self.state.refinery.capacity})\n"
                f"Research Level: {self.state.research_level}\n"
                f"Transport Hub: {self.state.transport_hub.level}/{HUB_MAX_LEVEL}\n"
                f"Demand Index: {self.state.market_demand}\n"
                f"Loan Balance: ${self.state.loan_balance:,}\n"
                f"Event: {self.state.event_message or 'None'}"
            )
        )
        self.scenario_desc.config(text=self.state.scenario.description)
        self.progress["value"] = (self.state.day / self.state.scenario.max_days) * 100

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

        self.news_label.config(text=self.state.news_message)
        self._draw_grid()
        self._update_buttons()
        self._update_competitor_panel()

    def _update_buttons(self) -> None:
        tile = self.selected_tile
        has_tile = tile is not None
        is_player_tile = tile is not None and tile.owner == "player"
        self.buy_button.config(
            text=f"Buy Land (${self.state.scenario.land_cost})",
            state=tk.NORMAL if has_tile and tile and tile.owner is None else tk.DISABLED,
        )
        self.survey_button.config(
            text=f"Survey (${SURVEY_COST})",
            state=tk.NORMAL if has_tile and is_player_tile else tk.DISABLED,
        )
        self.drill_button.config(
            text=f"Drill Well (${self.state.scenario.drill_cost})",
            state=tk.NORMAL if has_tile and is_player_tile and not tile.drilled else tk.DISABLED,
        )
        self.pump_button.config(
            text=f"Build Pump (${self.state.scenario.pump_cost})",
            state=tk.NORMAL
            if has_tile and is_player_tile and tile.drilled and not tile.has_pump and not tile.depleted
            else tk.DISABLED,
        )
        self.upgrade_button.config(
            text=f"Upgrade Pump (${PUMP_UPGRADE_COST})",
            state=tk.NORMAL
            if has_tile and is_player_tile and tile.has_pump and tile.pump_level < MAX_PUMP_LEVEL
            else tk.DISABLED,
        )
        self.storage_button.config(
            text=f"Add Storage (${self.state.scenario.storage_cost})",
            state=tk.NORMAL if has_tile and is_player_tile else tk.DISABLED,
        )
        self.refinery_button.config(
            text=f"Build Refinery (${REFINERY_BUILD_COST})",
            state=tk.NORMAL if self.state.refinery.level == 0 else tk.DISABLED,
        )
        self.upgrade_refinery_button.config(
            text=f"Upgrade Refinery (${REFINERY_UPGRADE_COST})",
            state=tk.NORMAL if self.state.refinery.active else tk.DISABLED,
        )
        self.research_button.config(
            text=f"Research Efficiency (${RESEARCH_COST})",
            state=tk.NORMAL if self.state.cash >= RESEARCH_COST else tk.DISABLED,
        )
        self.hub_button.config(
            text=f"Build Transport Hub (${HUB_BUILD_COST})",
            state=tk.NORMAL if not self.state.transport_hub.active else tk.DISABLED,
        )
        self.upgrade_hub_button.config(
            text=f"Upgrade Transport Hub (${HUB_UPGRADE_COST})",
            state=tk.NORMAL
            if self.state.transport_hub.active and self.state.transport_hub.level < HUB_MAX_LEVEL
            else tk.DISABLED,
        )
        self.trade_button.config(
            state=tk.NORMAL if economy.total_storage(self.state, "player") > 0 or self.state.petrol_storage > 0 else tk.DISABLED
        )
        self.sell_button.config(
            text="Sell Oil",
            state=tk.NORMAL if economy.total_storage(self.state, "player") > 0 else tk.DISABLED,
        )
        self.sell_petrol_button.config(
            text="Sell Petrol",
            state=tk.NORMAL if self.state.petrol_storage > 0 else tk.DISABLED,
        )

    def _update_competitor_panel(self) -> None:
        lines = ["Competitors:"]
        for competitor in self.state.competitors:
            lines.append(f"- {competitor.name}: ${competitor.cash:,}")
        self.competitor_label.config(text="\n".join(lines))

        if not self.state.contracts:
            self.contract_label.config(text="Contracts: None")
        else:
            contract_lines = ["Contracts:"]
            for contract in self.state.contracts:
                contract_lines.append(
                    f"- {contract.name}: {contract.delivered}/{contract.volume} ({contract.days_remaining}d)"
                )
            self.contract_label.config(text="\n".join(contract_lines))

    def _set_summary(self, snapshot: economy.EconomySnapshot) -> None:
        lines = ["End of Day Summary"]
        if snapshot.production:
            lines.append(f"Produced: {snapshot.production} barrels")
        if snapshot.refined:
            lines.append(f"Refined: {snapshot.refined} barrels")
        if snapshot.contract_delivered:
            lines.append(f"Contract delivered: {snapshot.contract_delivered} barrels")
        if snapshot.maintenance_cost:
            lines.append(f"Maintenance: ${snapshot.maintenance_cost}")
        if snapshot.interest_cost:
            lines.append(f"Interest: ${snapshot.interest_cost}")
        if snapshot.events:
            lines.extend(snapshot.events)
        self.summary_label.config(text="\n".join(lines))

    def _start_fx_loop(self) -> None:
        if self.fx_running:
            return
        self.fx_running = True
        self._tick_fx()

    def _tick_fx(self) -> None:
        self.fx_tick = (self.fx_tick + 1) % 120
        self._draw_grid()
        self.root.after(180, self._tick_fx)

    def _play_sound(self, action: str) -> None:
        if action in {"buy", "sell", "loan", "advance", "build"}:
            self.root.bell()
        elif action in {"error"}:
            self.root.bell()
            self.root.bell()
        else:
            self.root.bell()

    def _on_canvas_click(self, event: tk.Event) -> None:
        tile = self._tile_at(event.x, event.y)
        if tile:
            self.selected_tile = tile
            self._refresh_ui()

    def _tile_at(self, x: int, y: int):
        col = x // self.tile_size
        row = y // self.tile_size
        for tile in self.state.tiles:
            if tile.row == row and tile.col == col:
                return tile
        return None

    def _draw_grid(self) -> None:
        self.canvas.delete("all")
        grid_size = self.state.scenario.grid_size
        self.tile_size = min(MAP_PIXEL_SIZE // grid_size, 70)
        canvas_size = self.tile_size * grid_size
        self.canvas.config(width=canvas_size, height=canvas_size)
        self._draw_background(canvas_size)

        selection_pulse = 1 + (self.fx_tick % 6) * 0.08
        pump_pulse = 1 + (self.fx_tick % 6) * 0.1

        for tile in self.state.tiles:
            x0 = tile.col * self.tile_size
            y0 = tile.row * self.tile_size
            x1 = x0 + self.tile_size
            y1 = y0 + self.tile_size
            terrain_fill, terrain_detail = self._terrain_for_tile(tile.row, tile.col)
            fill = terrain_fill
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
                x0 + 2,
                y0 + 2,
                x1 - 2,
                y1 - 2,
                outline=terrain_detail,
                width=1,
            )
            self.canvas.create_rectangle(
                x0 + 4,
                y0 + 4,
                x1 - 4,
                y1 - 4,
                outline="#94a3b8",
                width=1,
            )
            self._draw_tile_texture(x0 + 4, y0 + 4, x1 - 4, y1 - 4)
            if tile.owner:
                owner_color = self._owner_color(tile.owner)
                self.canvas.create_rectangle(
                    x0 + 3,
                    y0 + 3,
                    x1 - 3,
                    y1 - 3,
                    outline=owner_color,
                    width=2,
                )
                self.canvas.create_rectangle(
                    x0 + 3,
                    y0 + 3,
                    x1 - 3,
                    y1 - 3,
                    fill=owner_color,
                    stipple="gray25",
                    outline="",
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
            if tile.owner == "player" and tile.has_pump and self.state.refinery.active:
                self._draw_smokestack(x0 + 6, y0 + 12, self.tile_size - 12)

            if tile is self.selected_tile:
                self.canvas.create_rectangle(
                    x0 + 3 - selection_pulse,
                    y0 + 3 - selection_pulse,
                    x1 - 3 + selection_pulse,
                    y1 - 3 + selection_pulse,
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

            if tile.has_pump:
                self.canvas.create_oval(
                    x0 + self.tile_size * 0.72,
                    y0 + self.tile_size * 0.08,
                    x0 + self.tile_size * 0.72 + 6 * pump_pulse,
                    y0 + self.tile_size * 0.08 + 6 * pump_pulse,
                    fill="#fbbf24",
                    outline="",
                )

        for tile in self.state.tiles:
            if tile.owner == "player" and tile.has_pump:
                self._draw_pipeline(tile, self.tile_size)
        self._draw_hub(canvas_size)

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

        sun_size = canvas_size * 0.16
        phase = (self.state.day_phase % 4) / 3
        sun_x = canvas_size * (0.15 + 0.7 * phase)
        sun_y = canvas_size * (0.08 + 0.08 * abs(0.5 - phase))
        if self.state.day_phase % 4 < 3:
            self.canvas.create_oval(
                sun_x,
                sun_y,
                sun_x + sun_size,
                sun_y + sun_size,
                fill="#fde047",
                outline="",
            )
        else:
            self.canvas.create_oval(
                sun_x,
                sun_y,
                sun_x + sun_size,
                sun_y + sun_size,
                fill="#e2e8f0",
                outline="",
            )

        cloud_color = "#e2e8f0"
        for i in range(3):
            x = canvas_size * (0.12 + i * 0.2)
            y = canvas_size * (0.12 + i * 0.05)
            self.canvas.create_oval(x, y, x + 50, y + 25, fill=cloud_color, outline="")
            self.canvas.create_oval(x + 20, y - 10, x + 60, y + 20, fill=cloud_color, outline="")
            self.canvas.create_oval(x + 40, y, x + 80, y + 28, fill=cloud_color, outline="")

        for x, y, size, color in self.state.decorations:
            self.canvas.create_oval(x, y, x + size, y + size, fill=color, outline="")

        self._draw_river(canvas_size)
        self._draw_grid_roads(canvas_size)

        contour_color = "#0f172a"
        for i in range(4):
            offset = canvas_size * (0.15 + i * 0.18)
            self.canvas.create_line(
                0,
                offset,
                canvas_size,
                offset + canvas_size * 0.08,
                fill=contour_color,
                width=2,
                stipple="gray25",
            )

        if self.state.day_phase % 4 == 3:
            self.canvas.create_rectangle(
                0, 0, canvas_size, canvas_size, fill="#0b1120", stipple="gray50", outline=""
            )

    def _draw_river(self, canvas_size: int) -> None:
        rng = random.Random(self.state.map_seed)
        points = []
        x = rng.randint(int(canvas_size * 0.1), int(canvas_size * 0.2))
        for step in range(7):
            y = int(canvas_size * (step / 6))
            x += rng.randint(-20, 25)
            x = max(10, min(canvas_size - 10, x))
            points.append((x, y))
        for i in range(len(points) - 1):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]
            self.canvas.create_line(x0, y0, x1, y1, fill="#38bdf8", width=10, smooth=True)
            self.canvas.create_line(x0, y0, x1, y1, fill="#0ea5e9", width=6, smooth=True)

    def _draw_grid_roads(self, canvas_size: int) -> None:
        grid = self.state.scenario.grid_size
        if grid <= 3:
            return
        step = canvas_size / grid
        for idx in range(1, grid):
            x = int(step * idx)
            y = int(step * idx)
            self.canvas.create_line(
                x, 0, x, canvas_size, fill="#1f2937", width=3, stipple="gray25"
            )
            self.canvas.create_line(
                0, y, canvas_size, y, fill="#1f2937", width=3, stipple="gray25"
            )

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

    def _draw_hub(self, canvas_size: int) -> None:
        if not self.state.transport_hub.active:
            return
        size = max(50, canvas_size * 0.18)
        x0 = canvas_size - size - 8
        y0 = canvas_size - size - 8
        self.canvas.create_rectangle(x0, y0, x0 + size, y0 + size, fill="#1f2937", outline="#94a3b8")
        self.canvas.create_polygon(
            x0 + size * 0.15,
            y0 + size * 0.25,
            x0 + size * 0.5,
            y0 + size * 0.05,
            x0 + size * 0.85,
            y0 + size * 0.25,
            fill="#475569",
            outline="",
        )
        self.canvas.create_rectangle(
            x0 + size * 0.25,
            y0 + size * 0.35,
            x0 + size * 0.75,
            y0 + size * 0.8,
            fill="#0f172a",
            outline="",
        )
        self.canvas.create_text(
            x0 + size / 2,
            y0 + size * 0.62,
            text=f"HUB {self.state.transport_hub.level}",
            fill="#f8fafc",
            font=("Helvetica", 8, "bold"),
        )
        self.canvas.create_line(
            x0 + size * 0.2,
            y0 + size * 0.9,
            x0 + size * 0.8,
            y0 + size * 0.9,
            fill="#38bdf8",
            width=2,
        )

    def _draw_smokestack(self, x0: int, y0: int, size: int) -> None:
        if not self.state.refinery.active:
            return
        drift = (self.fx_tick % 10) - 5
        self.canvas.create_rectangle(
            x0 + size * 0.75,
            y0 + size * 0.2,
            x0 + size * 0.88,
            y0 + size * 0.5,
            fill="#475569",
            outline="",
        )
        puff_color = "#94a3b8" if self.state.day_phase % 2 == 0 else "#cbd5f5"
        self.canvas.create_oval(
            x0 + size * 0.72 + drift,
            y0 + size * 0.12,
            x0 + size * 0.9 + drift,
            y0 + size * 0.28,
            fill=puff_color,
            outline="",
        )
        self.canvas.create_oval(
            x0 + size * 0.66 + drift,
            y0 + size * 0.02,
            x0 + size * 0.82 + drift,
            y0 + size * 0.18,
            fill=puff_color,
            outline="",
        )

    def _draw_tile_texture(self, x0: int, y0: int, x1: int, y1: int) -> None:
        color = "#64748b"
        step = 10
        for offset in range(0, int(x1 - x0), step):
            self.canvas.create_line(
                x0 + offset,
                y1,
                x0,
                y1 - offset,
                fill=color,
                width=1,
                stipple="gray25",
            )
        rng = random.Random(self.state.map_seed + int(x0 + y0))
        for _ in range(2):
            px = rng.randint(int(x0 + 2), int(x1 - 6))
            py = rng.randint(int(y0 + 2), int(y1 - 6))
            self.canvas.create_oval(
                px,
                py,
                px + 4,
                py + 4,
                fill=color,
                outline="",
            )

    def _terrain_for_tile(self, row: int, col: int) -> tuple[str, str]:
        rng = random.Random(self.state.map_seed + row * 31 + col * 17)
        roll = rng.random()
        if roll < 0.18:
            return "#0f766e", "#14b8a6"
        if roll < 0.4:
            return "#14532d", "#166534"
        if roll < 0.65:
            return "#4b5563", "#64748b"
        return "#7c5c3f", "#8b6b4c"

    def _draw_pipeline(self, tile, size: int) -> None:
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

    def new_game(self) -> None:
        scenario_name = self.scenario_var.get()
        scenario = next(s for s in SCENARIOS if s.name == scenario_name)
        self.state = new_game_state(scenario)
        self.selected_tile = None
        self._log("New game started.")
        self._refresh_ui()

    def save_game(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Black Oil Save", "*.json")],
        )
        if not path:
            return
        save_game(self.state, path)
        self._log(f"Game saved to {path}.")

    def load_game(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Black Oil Save", "*.json")])
        if not path:
            return
        self.state = load_game(path)
        self.scenario_var.set(self.state.scenario.name)
        self.selected_tile = None
        self._log(f"Game loaded from {path}.")
        self._refresh_ui()

    def toggle_sound(self) -> None:
        messagebox.showinfo("Sound", "Sound toggle is handled by system beeps in this prototype.")

    def toggle_tooltips(self) -> None:
        messagebox.showinfo("Tooltips", "Tooltips are not implemented in this refactor yet.")

    def show_about(self) -> None:
        messagebox.showinfo(
            "About Black Oil",
            "Black Oil - Frontier Drilling\n"
            "A strategy prototype inspired by classic oil boom simulations.",
        )

    def show_statistics(self) -> None:
        messagebox.showinfo(
            "Company Statistics",
            "Total Production Summary\n"
            f"- Oil Produced: {self.state.total_oil_produced} barrels\n"
            f"- Petrol Refined: {self.state.total_petrol_refined} barrels\n"
            f"- Contract Delivered: {self.state.total_contract_delivered} barrels\n",
        )

    def toggle_auto_refine(self) -> None:
        self.state.auto_refine = bool(self.auto_refine_var.get())
        self._refresh_ui()

    def buy_land(self) -> None:
        if not self.selected_tile:
            return
        success, message = leasing.buy_land(self.state, self.selected_tile)
        if not success:
            messagebox.showinfo("Land Purchase", message)
            return
        self._log(message)
        self._refresh_ui()

    def survey_tile(self) -> None:
        if not self.selected_tile:
            return
        success, message = drilling.survey_tile(self.state, self.selected_tile)
        if not success:
            messagebox.showinfo("Survey", message)
            return
        self._log(message)
        self._refresh_ui()

    def drill_well(self) -> None:
        if not self.selected_tile:
            return
        success, message = drilling.drill_well(self.state, self.selected_tile)
        if not success:
            messagebox.showinfo("Drill Well", message)
            return
        self._log(message)
        self._refresh_ui()

    def build_pump(self) -> None:
        if not self.selected_tile:
            return
        success, message = drilling.build_pump(self.state, self.selected_tile)
        if not success:
            messagebox.showinfo("Build Pump", message)
            return
        self._log(message)
        self._refresh_ui()

    def upgrade_pump(self) -> None:
        if not self.selected_tile:
            return
        success, message = drilling.upgrade_pump(self.state, self.selected_tile)
        if not success:
            messagebox.showinfo("Upgrade Pump", message)
            return
        self._log(message)
        self._refresh_ui()

    def add_storage(self) -> None:
        if not self.selected_tile:
            return
        tile = self.selected_tile
        if tile.owner != "player":
            return
        if self.state.cash < self.state.scenario.storage_cost:
            messagebox.showinfo("Insufficient Cash", "You need more cash to expand storage.")
            return
        tile.capacity += STORAGE_EXPANSION
        self.state.cash -= self.state.scenario.storage_cost
        self._log(f"Added storage on tile ({tile.row + 1}, {tile.col + 1}).")
        self._refresh_ui()

    def build_refinery(self) -> None:
        success, message = projects.build_refinery(self.state)
        if not success:
            messagebox.showinfo("Refinery", message)
            return
        self._log(message)
        self._refresh_ui()

    def upgrade_refinery(self) -> None:
        success, message = projects.upgrade_refinery(self.state)
        if not success:
            messagebox.showinfo("Refinery", message)
            return
        self._log(message)
        self._refresh_ui()

    def research_upgrade(self) -> None:
        success, message = projects.research_upgrade(self.state)
        if not success:
            messagebox.showinfo("Research", message)
            return
        self._log(message)
        self._refresh_ui()

    def build_hub(self) -> None:
        success, message = projects.build_hub(self.state)
        if not success:
            messagebox.showinfo("Transport Hub", message)
            return
        self._log(message)
        self._refresh_ui()

    def upgrade_hub(self) -> None:
        success, message = projects.upgrade_hub(self.state)
        if not success:
            messagebox.showinfo("Transport Hub", message)
            return
        self._log(message)
        self._refresh_ui()

    def trade_market(self) -> None:
        if economy.total_storage(self.state, "player") <= 0 and self.state.petrol_storage <= 0:
            return
        commodity = _TradeDialog.ask_commodity(self.root)
        if commodity is None:
            return
        if commodity == "oil":
            available = economy.total_storage(self.state, "player")
            market_price = self.state.price
        else:
            available = self.state.petrol_storage
            market_price = self.state.petrol_price
        if available <= 0:
            messagebox.showinfo("Trade Market", f"No {commodity} available to trade.")
            return
        offers = market.trade_offers(self.state)
        dialog = _OfferDialog(
            self.root,
            title="Trade Market",
            offers=offers,
            available=available,
            commodity=commodity,
            market_price=market_price,
        )
        result = dialog.show()
        if not result:
            return
        buyer, volume, revenue = result
        if commodity == "oil":
            economy.withdraw_oil(self.state, volume)
        else:
            self.state.petrol_storage -= volume
        self.state.cash += revenue
        buyer.demand = max(0, buyer.demand - volume)
        buyer.reputation = min(REPUTATION_MAX, buyer.reputation + 1)
        self._log(f"Traded {volume} barrels of {commodity} with {buyer.name} for ${revenue}.")
        self._refresh_ui()

    def sell_oil(self) -> None:
        success, message, revenue = production.sell_oil(self.state)
        if not success:
            messagebox.showinfo("Sell Oil", message)
            return
        self._log(f\"{message} Revenue: ${revenue}.\")
        self._refresh_ui()

    def sell_petrol(self) -> None:
        success, message, revenue = production.sell_petrol(self.state)
        if not success:
            messagebox.showinfo("Sell Petrol", message)
            return
        self._log(f\"{message} Revenue: ${revenue}.\")
        self._refresh_ui()

    def manage_contracts(self) -> None:
        offers = market.contract_offers(self.state)
        dialog = _OfferDialog(
            self.root,
            title="Contracts",
            offers=offers,
            available=economy.total_storage(self.state, "player"),
            commodity="oil",
            market_price=self.state.price,
            contract_mode=True,
        )
        result = dialog.show()
        if not result:
            return
        contract, volume, _revenue = result
        contract.volume = volume
        self.state.contracts.append(contract)
        self._log(f"Signed contract: {contract.name} for {contract.volume} barrels.")
        self._refresh_ui()

    def take_loan(self) -> None:
        success, message = finance.take_loan(self.state)
        if not success:
            messagebox.showinfo("Loan", message)
            return
        self._log(message)
        self._refresh_ui()

    def repay_loan(self) -> None:
        success, message = finance.repay_loan(self.state)
        if not success:
            messagebox.showinfo("Loan", message)
            return
        self._log(message)
        self._refresh_ui()

    def next_day(self) -> None:
        if self.state.day >= self.state.scenario.max_days:
            self._final_score()
            return
        self.state.day += 1
        snapshot = economy.advance_day(self.state)
        ai_events = ai.competitor_turns(self.state)
        for event in ai_events:
            snapshot.events.append(event)
        self._set_summary(snapshot)
        self._refresh_ui()
        if self.state.day == self.state.scenario.max_days:
            self._final_score()

    def _final_score(self) -> None:
        assets = (
            self.state.cash
            + economy.total_storage(self.state, "player") * self.state.price
            + self.state.petrol_storage * self.state.petrol_price
            - self.state.loan_balance
        )
        messagebox.showinfo(
            "Season Over",
            f"You finished with ${assets:,} in assets.\nThanks for playing Black Oil!",
        )

    def _log(self, message: str) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)


class _OfferDialog:
    def __init__(
        self,
        root: tk.Tk,
        title: str,
        offers: list,
        available: int,
        commodity: str,
        market_price: int,
        contract_mode: bool = False,
    ) -> None:
        self.root = root
        self.title = title
        self.offers = offers
        self.available = available
        self.commodity = commodity
        self.market_price = market_price
        self.contract_mode = contract_mode
        self.result: tuple | None = None

        self.window = tk.Toplevel(root)
        self.window.title(title)
        self.window.grab_set()
        self.window.resizable(False, False)

        tk.Label(self.window, text=f"{title} - {commodity.title()}", font=("Helvetica", 12, "bold")).pack(
            pady=(10, 6)
        )

        self.listbox = tk.Listbox(self.window, width=60, height=6)
        self.listbox.pack(padx=10)
        for offer in offers:
            if isinstance(offer, Buyer):
                price = offer.price_for(market_price)
                self.listbox.insert(
                    tk.END,
                    f"{offer.name} ({offer.category}) - Demand {offer.demand} @ ${price}",
                )
            else:
                self.listbox.insert(
                    tk.END,
                    f"{offer.name} - {offer.volume} barrels @ ${offer.price} ({offer.days_remaining} days)",
                )

        self.volume_var = tk.IntVar(value=min(available, offers[0].demand if offers else 0))
        self.volume_scale = tk.Scale(
            self.window,
            from_=0,
            to=min(available, TRADE_MAX_VOLUME),
            orient=tk.HORIZONTAL,
            label="Volume",
            variable=self.volume_var,
            length=280,
            command=self._update_revenue,
        )
        self.volume_scale.pack(pady=8)

        self.revenue_label = tk.Label(self.window, text="Revenue: $0")
        self.revenue_label.pack()

        buttons = tk.Frame(self.window)
        buttons.pack(pady=10)
        tk.Button(buttons, text="Confirm", command=self._confirm).grid(row=0, column=0, padx=6)
        tk.Button(buttons, text="Cancel", command=self._cancel).grid(row=0, column=1, padx=6)

        self.listbox.bind("<<ListboxSelect>>", lambda _event: self._update_revenue())
        self._update_revenue()

    def _selected_offer(self):
        selection = self.listbox.curselection()
        if not selection:
            return None
        return self.offers[selection[0]]

    def _update_revenue(self, _value: str | None = None) -> None:
        offer = self._selected_offer()
        if not offer:
            self.revenue_label.config(text="Revenue: $0")
            return
        volume = min(self.volume_var.get(), self.available)
        if isinstance(offer, Buyer):
            price = offer.price_for(self.market_price)
            revenue = volume * price
        else:
            revenue = volume * offer.price
        self.revenue_label.config(text=f"Revenue: ${revenue}")

    def _confirm(self) -> None:
        offer = self._selected_offer()
        if not offer:
            return
        volume = min(self.volume_var.get(), self.available)
        if volume <= 0:
            return
        if isinstance(offer, Buyer):
            revenue = volume * offer.price_for(self.market_price)
        else:
            revenue = volume * offer.price
        self.result = (offer, volume, revenue)
        self.window.destroy()

    def _cancel(self) -> None:
        self.window.destroy()

    def show(self):
        self.root.wait_window(self.window)
        return self.result


class _TradeDialog:
    @staticmethod
    def ask_commodity(root: tk.Tk) -> str | None:
        window = tk.Toplevel(root)
        window.title("Trade Market")
        window.grab_set()
        tk.Label(window, text="Select commodity to trade:").pack(padx=10, pady=8)
        selection = tk.StringVar(value="oil")
        tk.Radiobutton(window, text="Oil", variable=selection, value="oil").pack(anchor="w", padx=10)
        tk.Radiobutton(window, text="Petrol", variable=selection, value="petrol").pack(anchor="w", padx=10)
        result: list[str | None] = [None]

        def confirm() -> None:
            result[0] = selection.get()
            window.destroy()

        tk.Button(window, text="Confirm", command=confirm).pack(pady=8)
        root.wait_window(window)
        return result[0]


def _trade_offers(state: GameState, market_price: int) -> list[Buyer]:
    rng = random.Random(state.map_seed + state.day)
    offers = rng.sample(state.buyers, k=min(3, len(state.buyers)))
    for buyer in offers:
        buyer.demand = max(TRADE_MIN_VOLUME, min(TRADE_MAX_VOLUME, buyer.demand + rng.randint(-20, 20)))
    return offers


def _generate_contract_offers(state: GameState) -> list[Contract]:
    offers = []
    base_volume = random.randint(60, 140)
    for _ in range(3):
        volume = base_volume + random.randint(-20, 40)
        price = max(state.price + random.randint(-5, 25), state.scenario.price_min)
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
