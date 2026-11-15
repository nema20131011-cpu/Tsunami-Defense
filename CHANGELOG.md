# Changelog - Tsunami Defense

All notable changes, newest first. The same list is shown in-game under **Changelog** on the main menu.

## v1.6.0
- **Buyable extra plots:** 6 additional locked plots - a front beach column (earliest contact with waves) and a last-stand column right next to the city. Click a dark locked plot and press `B` or click the **BUY PLOT** button. They are deliberately expensive: $500 for the first, rising $250 each ($500 / $750 / $1000 / $1250 / $1500 / $1750 - $6,750 for all six), taking you from 12 to 18 build plots.

## v1.5.0
- **Boss waves:** every 5th wave is a single MEGA-TSUNAMI spanning all 3 lanes at once (6.5x HP, slow, 6x bounty, but a leak costs 50 city HP). Walls in any lane block it.
- **Win condition:** survive Wave 20 to win the campaign (victory screen), then optionally continue in Endless mode.
- **New tower - Mortar ($150, key `4`):** slow-firing shells (38 base damage) with 190px splash at half damage, which reaches waves in neighbouring lanes. Upgrades add damage, range, and a little fire rate.
- **New wave types:** SURGE waves (from Wave 2, 22% chance: 45% HP but 1.7x speed, thinner) and GOLDEN waves (from Wave 3, 10% chance: gold-coloured, 3x bounty).
- **Weather:** from Wave 10 the map darkens and rain falls, reaching full storm by Wave 13.
- **Stats that save:** best wave, total tsunamis destroyed, victories, and games played are stored in `stats.json` and shown on the main menu.
- **Damage numbers:** every projectile hit pops a floating damage number (gold = cannon, ice blue = frost, orange = mortar/splash).

## v1.4.1
- The game now downloads missing music files **by itself** at startup (`ensure_assets()` - URLs derived from `update_config.json`, with the repo as fallback). Since the game file is the one thing every launcher version auto-updates, existing players receive the real music automatically with this update - **no new zip needs to be sent to anyone, for this or future asset updates.** The launcher also supports this via `extra_files` for brand-new installs.

## v1.4.0
- Real background music: CC0 (public domain) orchestral tracks by Dizzy Crow from OpenGameArt - a calm loop for menu/build and a matching fight loop for waves, in `music/build.ogg` and `music/battle.ogg`. See `MUSIC_LICENSES.md`.
- The synthesized music remains in the game as an automatic fallback if the `music/` folder is missing.

## v1.3.0
- Main menu with Play / Changelog / Quit (calm music plays behind it).
- Repair towers and walls too, not just the city: select a built defense and press `T` or click the blue **REPAIR UNIT** button. It is a full repair in one click; the cost scales with the damage ($0.35 per missing HP, minimum $10) and the button shows the exact cost before you click.
- This changelog, in-game and as this file.

## v1.2.0
- Upgrades now cap at Level 10.
- Cannon upgrades also add +30 range and faster fire per level (0.55s -> 0.25s per shot). Frost upgrades also add +30 range per level, but its fire rate does not speed up (stays 0.85s).
- Difficulty rebalanced (it was effectively impossible): wave HP growth 1.55x -> 1.28x per wave, waves slower, starting money $170 -> $250, bigger bounties/bonuses, max 4 tsunamis per round, a leak costs at most 28 city HP instead of 38.

## v1.1.0
- Top-down view: ocean left, beach, 3 lanes of land, city rooftops right.
- 12 build plots (3 lanes x 4 columns) instead of 5 slots. Each wave rolls down a random lane; walls block only their own lane, towers shoot across lanes.
- Clickable REPAIR CITY button (the `R` key still works too).

## v1.0.0
- First release: defend the city against growing tsunami waves with Walls, Cannons, and Frost Towers; build / upgrade / sell; repair the city.
- 15 synthesized sound effects and 2 synthesized music tracks (calm build loop, fast battle loop) - no audio files needed.
- Auto-update launcher: checks GitHub before launch, mid-game update banner while playing.
