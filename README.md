# Suzuki Alstare Extreme Racing (PC, 2000) on modern PCs and the Steam Deck

## Why this exists

Suzuki Alstare Extreme Racing is a heavily tweaked Redline Racer, with improved bike models and what
feels like better handling. It's probably the best version of the game to play. On modern systems it
stops at a CD check, needs registry entries from its installer, plays no CD music under Proton, and
a modern pad's triggers can't be throttle and brake. This kit sorts that out, so it can be played
again.

The original Redline Racer has its own kit:
[redlineracer-pc-fix](https://github.com/framerateuk/redlineracer-pc-fix).

## What this does

Turns **your own** Suzuki Alstare Extreme Racing CD into a folder that runs on the Steam Deck
(Proton) or on Windows 10/11, with no installer and no registry entries:

- **Copied straight from the CD**: what the installer copies for a full install, without the long-gone
  online Game Service.
- **No registry**: the settings the game kept in the registry go in `registry.ini` beside the exe.
- **Direct3D through dgVoodoo2**: 640x480 rendered at your screen's height, 4:3 with black bars,
  held at 60 frames a second (with no limit, bikes crash at random or get stuck in the ground).
  **Dege's paletted-texture fix**, the one byte of his patch for this game that matters, is applied.
- **CD soundtrack** from OGG files ripped from your disc, with a fix so the game's CD player starts
  the music at all.
- **Gamepad**: an Xbox-style pad (the Steam Deck's included) is read directly, with analogue throttle
  and brake on the two triggers and analogue steering.
- No mouse pointer.

**No game files are in this repository.** Everything from the game comes from your disc when you
run `build.py`.

## What you need

| | |
|---|---|
| The game | The **Suzuki Alstare Extreme Racing CD** (Criterion / Ubi Soft, 2000, English, `SaerPC.exe` of 17 April 2000) as `.cue` + `.bin` or CloneCD `.ccd` + `.img`, with its audio tracks. `build.py` checks the exe and stops on another version. |
| Python | 3.8 or newer (python.org on Windows; already on macOS/Linux). |
| An OGG encoder | `oggenc` (vorbis-tools; Windows builds at rarewares.org) or `ffmpeg`, on the PATH. |
| dgVoodoo2 **2.79.3** | by Dege: [GitHub release v2.79.3](https://github.com/dege-diosg/dgVoodoo2/releases/tag/v2.79.3). Use 2.79.3: newer versions don't start under Wine/Proton. Keep the zip as downloaded. |
| ogg-winmm **v2025.01.16** | by AyuanX: [GitHub releases](https://github.com/ayuanx/ogg-winmm/releases). This exact release: `build.py` patches one call in its `winmm.dll` and checks the file first. Keep the zip as downloaded. |

## Build

```
python3 build.py Suzuki_Alstare_Extreme_Racing.cue --dgvoodoo dgVoodoo2_79_3.zip --ogg-winmm ogg-winmm_binary.zip
```

creates `SuzukiAlstareExtremeRacing/` with `game/` and `suzuki_launch.sh` (for the Steam Deck), in
about a minute. The same `game/` folder runs on Windows; `--windows` leaves out the launch script.
`--out DIR` puts the result somewhere else. The disc's original exe, readme, licence and English
manual are kept in `game/_spare/`.

## Play on the Steam Deck

1. Copy `SuzukiAlstareExtremeRacing/` to the Deck, for example to
   `/home/deck/Games/SuzukiAlstareExtremeRacing/`.
2. Desktop Mode: Steam > Add a Non-Steam Game > Browse > `.../game/SaerPC.exe`. Rename the shortcut
   "Suzuki Alstare Extreme Racing".
3. Properties > Compatibility: force **Proton 9.0**. Pin it rather than floating on Experimental.
4. Properties > Launch Options:
   ```
   /home/deck/Games/SuzukiAlstareExtremeRacing/suzuki_launch.sh %command%
   ```
5. Controller layout: start from the standard **Gamepad** layout and set these to keyboard keys:
   **Start = Enter**, **View = Esc**, **D-pad = arrow keys**. A race's pause and its pause menu are
   keyboard only.

## Play on Windows

Run `game/SaerPC.exe`. An Xbox pad works as on the Deck, except those three: use Enter, Esc and the
arrow keys on the keyboard, or map them in Steam or your pad software.

## Controls

| Pad | In a race | In the menus |
|---|---|---|
| Left stick | steer (analogue) | move |
| RT / LT | throttle / brake (analogue; both at once work) | |
| X | turbo | |
| RB / LB | gear up / down (manual gearbox; the default is automatic) | |
| Y | camera | |
| A | | choose |
| B | | back |
| D-pad (arrows) | | move |
| Start (Enter) | | choose |
| View (Esc) | pause | back |

Options > Controls rebinds them; the analogue triggers show there as "JOY RIGHT TRIGGER" and "JOY
LEFT TRIGGER". With the pad bindings the keyboard doesn't drive; delete the `Player0` lines from
`game/registry.ini` for the game's own keyboard set (arrows, Page Up / Down gears, Right Ctrl turbo).
Player 2 keeps the keyboard; a second XInput pad is joystick 2.

## Settings

- `game/registry.ini`: control bindings, volumes, video mode, texture detail, filtering (the game
  rewrites it when its Options menus close). The kit's copy sets English and the pad bindings.
- `game/menudata.ini`: player name, bike and rider, gears, geometry detail, view distance, field of
  view.
- Resolution: Options > Video lists 640x480 up to 1600x1200, all 4:3; dgVoodoo scales the picture
  to your screen either way.
- Music level: `CDDAVolume` in `game/winmm.ini` (the in-game slider may not reach the CD music).
- Deck renderer: `RENDERER=wined3d` before the script path in the launch options uses Wine's own
  Direct3D instead of dgVoodoo.

**Widescreen**: not included. AlphaYellow's widescreen fix widens the 3D, but the game places every
menu and HUD element in 640x480 units, so they'd all be stretched.

## Troubleshooting

- *"Please insert the ... CD"*: you're running the unpatched exe from `_spare/`.
- *No music*: on the Deck `launch.log` must show `WINEDLLOVERRIDES=...;winmm=n,b` (no log: the
  launch option is missing `%command%`), and `game/Music/Track02.ogg` must exist.
- *Bikes crash at random or stick in the ground*: the frame rate is unlimited. Keep `FPSLimit = 60`
  in `game/dgVoodoo.conf`.
- *Low-detail textures*: dgVoodoo's video memory set to 2 GB or more reads as negative to the game;
  keep `VRAM = 256`.
- *Judder on a G-Sync / FreeSync monitor*: turn variable refresh off for this game.

## What's in this repository

| File | What |
|---|---|
| `build.py` | Builds the folder: copies the CD's game files, patches the exe, rips the soundtrack, adds the wrappers and settings. Python standard library only. |
| `patch_exe.py` | The exe patches, each explained; adds a code section to the exe. Also runs on its own. |
| `caves.s` | The new code's source (x86 assembly). `python3 patch_exe.py --check-caves` re-assembles it with clang and checks it against the bytes in `patch_exe.py`. |
| `oggwinmm_fix.py` | A 5-byte fix to ogg-winmm v2025.01.16 (its "open cdaudio" string command crashes under Wine). |
| `disc.py` | Reads the CD image: `.cue`/`.bin` or `.ccd`/`.img`, ISO 9660 with Joliet names, and audio tracks. |
| `config/` | `registry.ini` (the game's registry settings, with the pad set up), dgVoodoo2's and ogg-winmm's settings. |
| `steamdeck/suzuki_launch.sh` | Proton launch wrapper: DLL overrides. |
| `docs/TECHNICAL.md` | How the game works and what each patch does. |

## Credits

- **Criterion Studios** made Suzuki Alstare Extreme Racing; **Ubi Soft** published it. Please own
  the game: this kit needs your disc.
- **Dege**: dgVoodoo2, and the paletted-texture fix from his patch for this game
  ([archive.org copy](https://web.archive.org/web/20220220115340id_/http://dege.fw.hu/Patches/bin/SuzukiAlstareExtremeRacingPatch.zip)).
  **AyuanX**: ogg-winmm.

## License

The scripts and docs in this repository: MIT (see `LICENSE`). The license covers only this
repository's own files, not the game, dgVoodoo2 or ogg-winmm.

Not affiliated with or endorsed by the game's rights holders.
