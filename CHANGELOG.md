# Changelog - Tsunami Defense

All notable changes, newest first. The same list is shown in-game under **Changelog** on the main menu.

## v1.4.0
- Real background music: CC0 (public domain) orchestral tracks by Dizzy Crow from OpenGameArt - a calm loop for menu/build and a matching fight loop for waves, in `music/build.ogg` and `music/battle.ogg`. See `MUSIC_LICENSES.md`.
- The synthesized music remains in the game as an automatic fallback if the `music/` folder is missing.
- The game now downloads missing music files **by itself** at startup (and the launcher can too, via `extra_files`). Since the game file is what every launcher auto-updates, existing players receive the real music automatically with this update - **no new zip needs to be sent to anyone, for this or future asset updates.**

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
