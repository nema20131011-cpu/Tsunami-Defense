# Tsunami Defense

A 2D Python / pygame game: defend the city on the right against tsunamis rolling in from the ocean on the left. Every wave is taller, tougher, and a bit faster — and later rounds send several waves in a row.

## Play it

Double-click `play_tsunami_defense.bat`, or run:

```
python tsunami_defense.py
```

## How to play

- **Top-down view:** ocean on the left, city on the right. Each tsunami rolls down one of 3 lanes (random each wave). Walls block only their own lane — towers shoot across lanes.
- **BUILD phase:** Click one of the 12 build plots (3 lanes x 4 columns) to select it, then build:
  - `1` — Wall — $50 — blocks the wave and soaks damage
  - `2` — Cannon — $100 — shoots the wave, reducing its power
  - `3` — Frost Tower — $120 — damages and slows the wave
- Click a built defense to select it: `U` upgrade ($75, max **Level 10**), `X` sell (70% refund)
- Upgrades raise damage + HP for both towers. **Cannon** also gains +30 range and faster fire per level (0.55s -> 0.25s per shot). **Frost** also gains +30 range per level, but its fire rate does *not* speed up - it stays 0.85s (its slow effect is its strength). Walls just gain a lot of HP.
- `R` — Repair city ($75, +20 HP) — or click the green **REPAIR CITY** button in the bottom-right
- `T` — Fully repair the selected tower/wall — or click the blue **REPAIR UNIT** button next to it. Cost scales with the damage ($0.35 per missing HP, min $10); the button shows the exact cost.
- The game starts at a **main menu** (Play / Changelog / Quit). The full version history is in `CHANGELOG.md` and on the menu's Changelog screen.
- `SPACE` — Start the next wave
- `P` — Pause, `Esc` — Quit
- `M` — Mute / unmute sound effects + music
- `N` — Music on / off (sound effects stay on)

## Sound effects

All sounds are generated in code (no audio files needed): cannon and frost shots, hits, splashes when a wave dies, thuds while a wave grinds on a wall, a boom when a wall breaks or the city is hit, a wave alarm, build / sell / upgrade / repair jingles, a round-clear jingle, and a game-over tune.

## Music

Also generated in code — two seamless loops over the same chord progression (Am – F – C – G):

- **Build phase:** a calm, slow loop (92 BPM) — soft chord pads, gentle bass, and a light arpeggio while you plan and build.
- **Wave phase:** a fast, driving battle loop (138 BPM) — pounding kick drum, driving bass, snare/hat percussion, chord stabs, and a lead melody. It kicks in automatically when a wave starts, switches back when you clear the round, pauses when you pause, and fades out on game over.
- Destroy a wave before it reaches the city to earn money + a round-clear bonus.
- If a wave hits the city, the city loses HP. At 0 HP it's game over — press `Enter` to play again.

## Tips

- Spread Walls across all 3 lanes — a wave in an unwalled lane sails straight to the city. Towers cover every lane, so concentrate cannons/frost wherever you like.
- Frost + Cannon is a strong combo: frost slows, cannon finishes.
- Upgrade a good tower before building a weak extra one in later waves.

## Auto-updates via GitHub (launcher)

Players should start the game with `play_tsunami_defense.bat` (it runs `launcher.py`). The launcher checks GitHub before starting, downloads a newer game if there is one, then launches it. While playing, the game also checks every 60 seconds and shows a gold banner if an update appears mid-game: finish, close, then run the launcher to get it. Nothing is ever replaced mid-game.

### One-time setup (repo owner)

1. Create a **public** GitHub repo (public so the raw links work without a login).
2. Edit `update_config.json`: replace `YOUR_USERNAME` and `YOUR_REPO` with your repo. If your default branch is not `main`, change `main` in both URLs too.
3. Upload these two files to the **root** of the repo: `tsunami_defense.py` and `version.txt`.
4. Send your friend a zip of this whole folder (with the filled-in `update_config.json`). They need Python + pygame installed, same as you.

### Releasing an update

1. Change `VERSION = "1.0.0"` near the top of `tsunami_defense.py` to the new number, e.g. `1.1.0`.
2. Put that same number in `version.txt` (it must match exactly).
3. Upload both files to GitHub, replacing the old ones.
4. Anyone already playing sees the banner within about a minute, and the launcher updates them automatically on their next start. The launcher sanity-checks the download and keeps the old version as `tsunami_defense.py.bak`.
