# Music licenses - Tsunami Defense

The background music in the `music/` folder is **CC0 (public domain dedication)** - not copyrighted, free for any use, no attribution legally required. Credit is given here voluntarily because the artist earned it.

## Tracks used

Both tracks come from the same pack, **"Desert calmness and fighting (orchestral)" by Dizzy Crow**, so the calm and battle music share one style:

- Pack page: https://opengameart.org/content/desert-calmness-and-fighting-orchestral-141
- License: **CC0** (verified on the pack page, which carries the CC0 license badge)

| Game file | Original file | Used for |
|---|---|---|
| `music/build.ogg` | `Negev Desert Loop.wav` | Menu / build phase (calm loop, ~42s) |
| `music/battle.ogg` | `Negev Fight Loop.wav` | Wave / battle phase (fight loop, ~37s) |

Original file URLs:
- https://opengameart.org/sites/default/files/Negev%20Desert%20Loop.wav
- https://opengameart.org/sites/default/files/Negev%20Fight%20Loop.wav

The originals are WAV; they were converted to OGG Vorbis (quality 5) with ffmpeg only to reduce size (about 14 MB -> 1.4 MB total). No other changes were made.

## Fallback music

If the `music/` folder is missing, the game falls back to its original fully synthesized music (generated in code, no files, no licensing involved). Distribution note: the game file itself downloads these tracks from GitHub at startup if they are missing (and the launcher can fetch them too), so existing players receive the music automatically with a normal game update - no re-zipping or re-sending needed.

## Sound effects

All sound effects are synthesized in code. No external audio, no licensing involved.
