#!/usr/bin/env python3
"""Build a ready-to-run Suzuki Alstare Extreme Racing folder for modern PCs from your own CD.

Usage:
  python3 build.py DISC.cue|DISC.ccd --dgvoodoo DGVOODOO.zip --ogg-winmm OGG-WINMM.zip [--out DIR] [--windows]

  DISC          your Suzuki Alstare Extreme Racing CD (Criterion / Ubi Soft, 2000, English) as .cue + .bin or
                .ccd + .img, with its audio tracks
  --dgvoodoo    dgVoodoo2 2.79.3 zip (or its unpacked folder)
  --ogg-winmm   ogg-winmm v2025.01.16 release zip (or folder)
  --out         where to create SuzukiAlstareExtremeRacing/ (default: this folder)
  --windows     a folder for Windows only: the same game/ folder, without the Steam Deck launch script

Needs Python 3.8+ and an Ogg Vorbis encoder on the PATH: oggenc (vorbis-tools) or ffmpeg.
Nothing from the game is in this repository: every game file comes from your disc.
"""
import argparse, hashlib, os, shutil, struct, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import disc, oggwinmm_fix, patch_exe

PATCHED_MD5 = "559badab275639000d72a97e86167b95"
# What the installer copies for a full install: "Game Data" and "Program Executable Files" (every file is read from
# the disc), without the Ubi Soft Game Service client (online, long gone)
FOLDERS = ["Overlays", "RIDERS", "bikes", "common", "dcui", "sound", "tracks", "misc"]
FILES = ["menudata.ini", "gameinst.ini", "type.ini", "title.txt"]
SPARE = [("SaerPC.exe", "SaerPC.exe"), ("License.txt", "License.txt"), ("Readme.txt", "README-2000.TXT"),
         ("Manual/ManUK.pdf", "Manual-UK.pdf")]


def md5(data): return hashlib.md5(data).hexdigest()


def encoder():
    if shutil.which("oggenc"): return lambda wav, ogg: ["oggenc", "-Q", "-q", "7", wav, "-o", ogg]
    if shutil.which("ffmpeg"):
        return lambda wav, ogg: ["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "7", ogg]
    sys.exit("needs oggenc (vorbis-tools) or ffmpeg on the PATH to encode the soundtrack")


def rip(tracks, music):
    enc = encoder(); os.makedirs(music, exist_ok=True); zero = bytes(2352); n = 0
    with tempfile.TemporaryDirectory() as tmp:
        for t in tracks:
            if t.kind != "AUDIO": continue
            data = disc.audio(t)          # INDEX 01 to the next track's start
            tail = 0                      # minus up to 2 s of digital silence at the end (the next track's pregap)
            while tail < 150 and data[len(data) - (tail + 1) * 2352:len(data) - tail * 2352] == zero: tail += 1
            if tail: data = data[:len(data) - tail * 2352]
            wav = os.path.join(tmp, f"track{t.n:02d}.wav")
            with open(wav, "wb") as o:
                o.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
                        struct.pack("<IHHIIHH", 16, 1, 2, 44100, 176400, 4, 16) + b"data" +
                        struct.pack("<I", len(data)) + data)
            subprocess.run(enc(wav, os.path.join(music, f"Track{t.n:02d}.ogg")), check=True); os.remove(wav)
            print(f"  Music/Track{t.n:02d}.ogg  {len(data) / 2352 / 75:6.1f} s"); n += 1
    if n != 10: sys.exit(f"expected 10 audio tracks (the game's music), found {n}: is the image missing them?")


def take(src, member):
    """Bytes of the file whose path ends with `member` (case-insensitive) in a zip or folder."""
    want = member.lower()
    if os.path.isdir(src):
        for d, _, fs in os.walk(src):
            for f in fs:
                p = os.path.join(d, f)
                if os.path.relpath(p, src).replace(os.sep, "/").lower().endswith(want): return open(p, "rb").read()
    else:
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                if name.lower().endswith(want): return z.read(name)
    sys.exit(f"{member} not found in {src}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("disc"); ap.add_argument("--dgvoodoo", required=True); ap.add_argument("--ogg-winmm", required=True)
    ap.add_argument("--out", default=HERE); ap.add_argument("--windows", action="store_true")
    a = ap.parse_args()

    tracks = disc.tracks(a.disc)
    data = [t for t in tracks if t.kind != "AUDIO"]
    if not data: sys.exit("no data track in " + a.disc)
    dt = disc.DataTrack(data[0])
    entries = {p.lower(): (p, is_dir, l, s) for p, is_dir, l, s in dt.walk(joliet=True)}
    if "saerpc.exe" not in entries: sys.exit("no SaerPC.exe on this CD: it isn't the Suzuki Alstare disc the kit was made for")
    got = md5(dt.read_file(*entries["saerpc.exe"][2:]))
    if got != patch_exe.MD5:
        sys.exit(f"this CD's SaerPC.exe is not the 17 April 2000 one the kit was made for (MD5 {got}); "
                 "nothing else is supported yet")
    winmm = oggwinmm_fix.patch(take(a.ogg_winmm, "winmm.dll"))    # before anything is written: the release must match

    pkg = os.path.join(os.path.abspath(a.out), "SuzukiAlstareExtremeRacing"); game = os.path.join(pkg, "game")
    if os.path.exists(pkg): sys.exit(f"{pkg} already exists: move or delete it first")

    print("1/5 game files from the CD")
    roots = tuple(f.lower() + "/" for f in FOLDERS)
    for key, (p, is_dir, l, s) in entries.items():
        if not (key + "/").startswith(roots): continue
        dst = os.path.join(game, *p.split("/"))
        if is_dir: os.makedirs(dst, exist_ok=True)      # the empty folders too
        else: dt.copy_file(l, s, dst)
    for f in FILES:
        dt.copy_file(*entries[f.lower()][2:], os.path.join(game, f))
    for f, dst in SPARE:
        dt.copy_file(*entries[f.lower()][2:], os.path.join(game, "_spare", dst))

    print("2/5 exe patches")
    out = patch_exe.patch(dt.read_file(*entries["saerpc.exe"][2:]))
    if md5(out) != PATCHED_MD5: sys.exit("patching gave an unexpected SaerPC.exe")
    open(os.path.join(game, "SaerPC.exe"), "wb").write(out)

    print("3/5 soundtrack")
    rip(tracks, os.path.join(game, "Music"))

    print("4/5 wrappers and settings")
    for member, name in [("MS/x86/DDraw.dll", "ddraw.dll"), ("MS/x86/D3DImm.dll", "d3dimm.dll")]:
        open(os.path.join(game, name), "wb").write(take(a.dgvoodoo, member))
    open(os.path.join(game, "winmm.dll"), "wb").write(winmm)
    for f in ("dgVoodoo.conf", "winmm.ini", "registry.ini"):     # registry.ini: language and the pad bindings
        shutil.copyfile(os.path.join(HERE, "config", f), os.path.join(game, f))

    print("5/5 Steam Deck launch script" if not a.windows else "5/5 done")
    if not a.windows:
        launch = os.path.join(pkg, "suzuki_launch.sh")
        shutil.copyfile(os.path.join(HERE, "steamdeck", "suzuki_launch.sh"), launch); os.chmod(launch, 0o755)
    print(f"\ndone: {pkg}  (see README.md)")


if __name__ == "__main__":
    main()
