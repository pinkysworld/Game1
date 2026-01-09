# Black Oil - Frontier Drilling

A macOS-friendly, single-player strategy game inspired by Sierra's classic oil boom simulations. Manage land, drill for oil, build pumps, and compete against rival crews while riding a volatile market to finish the season with the highest assets possible.

## Gameplay Highlights
- **Scenarios** with different grids, budgets, and market swings.
- **Difficulty levels** that tune cash, rivals, and market volatility.
- **Competitors** that buy land, drill, pump, upgrade, and sell against you.
- **Surveys** to estimate reserves before drilling.
- **Pump upgrades** to boost daily production.
- **Contracts** that reward fixed-price deliveries.
- **Loans** that help fund expansion (with interest).
- **Save & load** support to continue your campaign later.
- **Styled map visuals** with themed backdrops and landmark art.
- **Sound effects** with a toggle to mute or enable audio cues.

## Controls
- Click a tile on the map to select it.
- Use the action buttons on the right panel to manage that tile.
- Advance the day to trigger production, competitor moves, and market changes.
- Save or load from the panel at any time.

## Requirements
- Python 3.10+
- Tkinter (bundled with Python on macOS)

## Run the game
```bash
python3 src/main.py
```

## Scenarios
- **Frontier Boom**: Balanced market with steady reserves and moderate costs.
- **Desert Wildcat**: Higher drilling costs, sparser oil, but bigger price swings.
- **Coastal Rush**: Compact grid, high reserves, and fierce competition.
- **Mountain Strike**: Rocky terrain with high yields and steep operating costs.
- **Marshland Drift**: Winding wetlands with scattered reserves and calmer markets.

## Difficulty Levels
- **Easy**: More starting cash, calmer rivals, fewer negative events.
- **Standard**: Balanced competition and classic volatility.
- **Hard**: Lean budgets, aggressive rivals, and sharper market swings.

## Notes
- The season ends after the configured number of days for the scenario.
- Save files are stored as JSON for easy sharing or modding.
