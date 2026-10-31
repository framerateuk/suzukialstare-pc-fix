# How it works

Notes on Suzuki Alstare Extreme Racing (Criterion Studios / Ubi Soft, 2000), the English CD,
`SaerPC.exe` of 17 April 2000 (MD5 `6decadfaea8787fe4653f0078da2b1ce`). Addresses are virtual
addresses in that exe.

## The disc and the installer

Track 1 is the data track; tracks 2-11 are the music. The game is RenderWare 3's Direct3D 7 driver
on DirectDraw, with the Dreamcast version's menus. The InstallShield 5 installer's `data1.cab` holds
only the file list; every installed file is read from the disc's own folders. `build.py` copies what
a full install puts in the game folder ("Game Data" and "Program Executable Files"), using the disc's
Joliet names, without the Ubi Soft Game Service client (online, long gone). Left out: the installer,
autorun, DirectX 7, the Acrobat Reader installers and the manuals (the English one goes to
`_spare/`).

The installer also wrote `HKLM\Software\Criterion Studios\Suzuki Alstare Extreme Racing\1.00.000`,
which the game reads and writes for its settings; its writes never create the key, so without the
installer nothing was saved.

## The patches

`patch_exe.py` adds a section `.rdeck` (VA 0x559000, 4 KB, at the end of the file) holding the new
code from `caves.s`. Its header lists each site's bytes and how it was found. Only the pad code
carried over from Redline Racer; every site was found again.

| Patch | Hooks | Was | Now |
|---|---|---|---|
| `nocd` | the "Please insert the ... CD" box loop 0x420ba0 -> its CD search 0x402f80 (registry `CD`, else a CD-ROM drive labelled `SAER`) | Under Wine no folder is a CD-ROM drive with that label | Returns "found" at once; the CD root starts as `.\` (the game folder), as in Dege's exe |
| `cdinstall` | the path set-up 0x43c160: the registry DWORD `CDInstall` (0x43c1ac) | Not 0 = every data file from the CD | Always 0: everything from the exe's folder |
| `noreg` | the three registry helpers: 0x43c000 string read, 0x43c080 DWORD read, 0x43c100 DWORD write | The installer's HKLM key | `registry.ini` beside the exe, section `[Settings]`, `name=value` |
| `pad` | the input pump 0x446fc0's joystick read (0x446fda -> 0x447a60); the joystick count's store 0x446ccf | DirectInput: under Proton an Xbox pad's triggers are one Z axis (both held = neither), and the game binds no Z anyway | Joystick n written from the n-th connected XInput pad: left stick = X / Y, RT / LT = the two "sliders" (0..1 each), buttons A 0, B 1, X 2, Y 3, LB 4, RB 5, D-pad 7-10, View 11, Start 12, L3 13, R3 14. No XInput pad: the game's own read. An XInput pad DirectInput didn't list is read too |
| `sliders` | the race controls' joystick table 0x407cb8 and the Controls screen's name table 0x41b1a0 | The Controls screen could bind the two sliders but the race ignored them, and they had no names | A slider binding gives its analogue value, so RT / LT can be throttle / brake; named "JOY RIGHT TRIGGER" / "JOY LEFT TRIGGER" |
| `cdplay` | the Dive CD player's Play method 0x4a42c0: its `jl` after the status call (0x4a42f4) | Before playing it checks that the *current* track is audio; ogg-winmm says track 0 until something plays, so Play returned before `MCI_PLAY`: no music at all | That answer is let through, as the Seek method (0x4a46f0) already does |
| `nopal` | Dege's byte: the Direct3D driver's texture-format callback 0x46c2b0 (0x46c336) | Paletted texture formats were registered | Skipped: "makes the game avoid utilizing paletted textures" |
| `nopointer` | the menu draw's pointer call 0x415bf5 (`dcui\pointer.bmp`) | The menus drew a mouse pointer | Not drawn; the mouse still clicks |
| `nocursor` | `RegisterClassA` "RenderWareSkelClass": its `LoadCursorA(0, IDC_ARROW)` (0x447df0) | The class had the arrow | No class cursor |

**Dege's patch.** Dege (dgVoodoo2's author) published a patched `saerpc.exe` for this game, a whole
replacement exe ([archive.org copy](https://web.archive.org/web/20220220115340id_/http://dege.fw.hu/Patches/bin/SuzukiAlstareExtremeRacingPatch.zip));
PCGamingWiki's fix for "Game doesn't start" is "dgVoodoo 2 and Dege's patch". This kit doesn't use
his exe: it applies the one change his notes describe, `nopal`, to the disc's own exe, and its own
`nocd` matches his choice of `.\` as the CD root.

Not patched: the logos (any key or button already skips them), a web browser (the exe imports no
`ShellExecute`), a frame limiter or busy wait (there is none), the resolution, the online Game
Service (not installed, so it stays off).

## Picture

Options > Video lists 640x480 to 1600x1200 at 16 bits, all 4:3; 640x480 by default. dgVoodoo2
2.79.3: `Resolution = max` renders at the screen's height, `ScalingMode = stretched_ar` keeps 4:3
with black bars, vsync, `FPSLimit = 60`. dgVoodoo also offers DXT texture support, which the game
uses for its best texture level: with no setting it picks 5 (the `.dds` textures) when DXT is there,
else it goes by video memory, read as a *signed* number (2 GB or more would read as negative and
give the lowest textures; 256 MB is right).

Widescreen: AlphaYellow's widescreen fix replaces the resolution list with one wide mode and widens
the 3D cameras, but the game places every 2D element in 640x480 units scaled separately in x and y
(the menus 0x415051, the race HUD 0x41ef00 and the HUD code around it), so every menu and HUD
element would be stretched. It isn't used.

**Frame rate.** The race takes the frame time from `timeGetTime` (1 ms steps), clamps it to 200 ms
and runs 1-3 physics sub-steps a frame (0x43cc30); a 0 ms frame is a zero step. With no limit, bikes
crash at random or stick in the ground. dgVoodoo's vsync and `FPSLimit = 60` hold 60.

## Music

Criterion's Dive library opens the MCI `cdaudio` device by type (no drive letter), sets TMSF and
plays a track from / to, without notify, watching the device from a `timeSetEvent` timer
(0x4a5143). Nothing waits for a notification. Each track is ripped from its INDEX 01 to the next
track's start minus the 2 seconds of digital silence there (the disc's cue has no INDEX 00, so that
silence is the next track's pregap). The in-game music slider goes through the `mixer*` API, which
ogg-winmm passes on to the real winmm, so it may not reach the music; `CDDAVolume` in `winmm.ini`
does.

## Pad

Each of the eight race controls (left, right, accelerate, brake, turbo, gear up, gear down, camera)
is bound to one input, saved as `Player0<Control>1 / 2 / 3` (type / parameter / digital) in
`registry.ini`. Joystick parameters (0x407b16): 0 / 1 = stick left / right, 2 / 3 = up / down,
12 / 13 = slider 1 / 2 (`sliders`), 14 + n = button n. The menus read the pad themselves (0x414550:
button 0 = choose, 1 = back, 7-10 and the stick = move); a race's pause (Esc) and its pause menu
are keyboard only, hence the Steam Input keys on the Deck.

## ogg-winmm

ogg-winmm v2025.01.16 answers the string command "open cdaudio" by passing `MCI_OPEN` on to the
real winmm with a NULL parameter block. Windows' winmm fails and the result is ignored; Wine's
writes the device ID back through the NULL pointer, an access violation inside `winmm.dll`.
`oggwinmm_fix.py` replaces that one call with `add esp,0x10 ; xor eax,eax` (the same stack, result 0).
