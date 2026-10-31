#!/usr/bin/env python3
"""Patch Suzuki Alstare Extreme Racing's exe (the disc's SaerPC.exe, 1,179,648 bytes, MD5
6decadfaea8787fe4653f0078da2b1ce, linked 17 Apr 2000, MSVC; Criterion Studios / Ubi Soft, version 1.00.000) into a
copy.

  patch_exe.py <SaerPC.exe> <out.exe>   write the patched exe (refuses, writes nothing, on any unexpected byte)
  patch_exe.py --check-caves            re-assemble caves.s with clang and compare with CAVE below

New code (caves.s, assembled bytes in CAVE) goes into a section the patch adds: ".rdeck", VA 0x559000, 0x1000 bytes
at file offset 0x120000 (the end of the file), readable / writable / executable; its variables from 0x559c00. The
section table had room for a seventh entry (it ended at 0x2e8, the first section starts at 0x1000); SizeOfImage
0x159000 -> 0x15a000. The exe has no checksum, no relocations and already says "relocations stripped": it always
loads at 0x400000. Every section's file offset equals its RVA, so file offset = VA - 0x400000.

Each patch is described by what it hooks and how it was found (the way Redline Racer's patch_exe.py, the same
Criterion engine, describes its own), so it can be found again in another build. Addresses are this exe's.

  rdeck       the section (above) with the code of caves.s.
  nocd        the CD check. Found from the "Please insert the Suzuki Alstare Extreme Racing CD" / "CD Error"
              MessageBoxA loop (0x420ba0): it calls 0x402f80, which takes the drive letter from the registry
              value "CD", else tries D: to Z: and A: to C: for a CD-ROM drive (GetDriveTypeA = 5) whose volume
              label is "SAER" (0x403050). 0x402f80 now returns 1 ("found") at once; the CD root it would fill in
              keeps its starting value, now ".\\" instead of "d:\\" (0x51661c: the game folder, as Dege's patch
              below does). Nothing is read from it: see cdinstall.
  cdinstall   the data folder. The path set-up 0x43c160 reads the registry DWORD "CDInstall" (0x43c1ac) and, when
              it is not 0, reads all data from the CD (0x43a820: CD root or exe folder). The read now gives 0
              every time ("call" -> "mov eax, 1", "mov edi, [esp+8]" -> "xor edi, edi"): everything from the
              exe's folder, as the installer's full install (CDInstall=0) does, with or without registry.ini.
  noreg       the registry. The game keeps its settings in HKLM\\Software\\Criterion Studios\\Suzuki Alstare
              Extreme Racing\\1.00.000 (written by the installer; the game's own writes open the key but never
              create it): control bindings (Player0Left1 ...), volumes, video mode, texture detail and filtering,
              gloss mapping, language. All of it goes through three helpers, found from that key string
              (0x5165cc): 0x43c000 string read, 0x43c080 DWORD read, 0x43c100 DWORD write. Their first bytes now
              jump to regstr / regget / regset (caves.s), which use registry.ini beside the exe (section
              [Settings], name=value). The other Reg* calls are the online code's (Ubi Soft "Game Service"
              GSGame.dll, not on the disc) and Criterion's Dive library's own bookkeeping, none needed.
  pad         the joystick. The input pump 0x446fc0 (found from its PeekMessageA loop) reads joysticks 1..count
              ([0x54f52c]) with 0x447a60 (found from the "DirectInputCreate 5.0 FAILED - no joystick support"
              set-up and the vtable calls Poll [+0x64] / GetDeviceState(0x50 = sizeof DIJOYSTATE) [+0x24]; it
              fills X Y Z Rx Ry Rz as floats -1..1 (* 0.001), two sliders 0..1 (* 1/65536), 20 button bits) and
              hands each reading to the current input handler as event 0x16. Under Proton an Xbox pad's triggers
              share DirectInput's Z axis (both held = neither), and the game binds no Z anyway, so the pump's call
              (0x446fda) now goes to joyread, which writes joystick n from the n-th connected XInput pad (left
              stick, RT / LT as the two sliders, the buttons; docs/TECHNICAL.md "Pad"). With no XInput pad the game's own
              read runs. The count's store after DirectInput's set-up (0x446ccf, "mov [0x54f52c], eax") calls
              setcount: also an XInput pad DirectInput did not list is read.
  sliders     the race controls (0x407920: eight controls per player, each a binding {type, parameter, value};
              type 0x16 = joystick) read a joystick binding through a jump table on the parameter (0x407cb8): 0-3
              the stick's four directions, 14-29 buttons 0-15. The Controls screen also binds DirectInput's two
              sliders (parameters 12 and 13, 0x4105b2 / 0x4105de) but the table sent both to "nothing" (0x407c41).
              Entries 12 and 13 now point to slider0 / slider1: the slider's value (0..1), so RT / LT work as
              analogue throttle / brake. The Controls screen's names for them (the name function 0x41a8d0, its
              joystick table 0x41b1a0, entries 12 / 13 had none) point to name12 / name13: "JOY RIGHT TRIGGER" /
              "JOY LEFT TRIGGER".
  cdplay      the CD music. Criterion's Dive CD player starts a track with Seek (0x4a46f0) then Play
              (0x4a42c0); both first run its status method (0x4a4840), which ends by checking the type of the
              current track (MCI_STATUS_CURRENT_TRACK at 0x4a47e0, then MCI_CDA_STATUS_TYPE_TRACK) and returns
              0x80400008 when it is not audio. ogg-winmm reports current track 0 until something plays (a real drive
              reports the track just sought to), so the answer is "other". Seek accepts 0x80400008; Play returned
              on it before MCI_PLAY, so no music ever played (Deck trace, 24 Oct 2026). Play's "jl" after the status
              call (0x4a42f4) now goes to cdplay, which lets 0x80400008 through as Seek does.
  nopal       Dege's patch (the dgVoodoo2 author, "SuzukiAlstareExtremeRacingPatch.zip", see docs/TECHNICAL.md): "makes
              the game avoid utilizing paletted textures". In the Direct3D driver's texture-format enumeration
              callback (0x46c2b0) a paletted format (DDPF flags & 0x29) now ends the callback ("jne 0x46c33e" ->
              "jne 0x46c394", return 1 = go on enumerating) instead of being registered. One byte, 0x46c336.
  nopointer   the menus draw their own mouse pointer (dcui\\pointer.bmp, loaded at 0x414aae into [0x51df80])
              every frame (0x416320, called from the menu draw at 0x415bf5). That call is now a 5-byte nop (the
              mouse still clicks menu items, unseen).
  nocursor    the window class (RegisterClassA "RenderWareSkelClass", 0x447e0f) had LoadCursorA(0, IDC_ARROW) as
              its cursor: the call (0x447df0) is now "add esp, 8; xor eax, eax" (no class cursor). The skeleton
              already hides the Windows cursor full screen (ShowCursor(0), 0x448007).

Not patched (docs/TECHNICAL.md): the start-up logos (Ubi Soft, Criterion, RenderWare: dcui\\*.png, 3 s
each, 0x414d80) already end on any key or pad button; no web browser (the exe imports no ShellExecute; its HTTP code
is the online part's); the frame rate (no limiter, no busy wait: the physics take the frame time from the skeleton's
timer, clamp it to 200 ms and run 1-3 sub-steps, 0x43cc30; dgVoodoo's vsync and FPSLimit hold 60 frames a second);
the resolution (the game's own list, 640x480 to 1600x1200, all 4:3; docs/TECHNICAL.md "Picture").
"""
import hashlib, os, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE, MD5 = 1179648, "6decadfaea8787fe4653f0078da2b1ce"
def T(va):                             # file offset = VA - 0x400000 (.text .. .data raw parts)
    assert 0x401000 <= va < 0x51e000, hex(va)
    return va - 0x400000

def rel32(src, dst, op):               # e8 / e9 at src (5 bytes) -> dst
    return bytes([op]) + (dst - (src + 5)).to_bytes(4, "little", signed=True)

SECT_VA, SECT_RVA, SECT_OFF, SECT_SIZE = 0x559000, 0x159000, 0x120000, 0x1000
CAVE_VA = SECT_VA
CAVE = bytes.fromhex(
    "608b7424288b44242448e8e900000085c07513833d249c550000750661e93eeaeeff6131c0c3e80700000061b8010000"
    "00c38b1d089c5500a10c9c5500e873000000d91ea1109c5500e867000000d9e0d95e04c7460800000000a1149c5500e8"
    "51000000d95e0ca1189c5500e844000000d9e0d95e10c7461400000000a1209c5500e85d000000d95e18a11c9c5500e8"
    "50000000d95e1c31c9bff093550031d20fb7045785c374030fabd14283fa0f72ef894e20c389c19931d029d02da00f00"
    "007f03d9eec33d5f7000007e05b85f70000050db0424d80d109455005885c97902d9e0c383f8087d03d9eec350db0424"
    "d80d1494550058c36089c5833d049c550000753cc705049c550001000000beb0945500bb0300000056ff156c204c0085"
    "c07417681894550050ff1570204c0085c07407a3009c5500eb0683c6104b75d831f631ff833d009c550000747631db68"
    "409c550053ff15009c550085c0755e39ef7559be010000000fb705449c5500a3089c55000fb605469c5500a31c9c5500"
    "0fb605479c5500a3209c55000fbf05489c5500a30c9c55000fbf054a9c5500a3109c55000fbf054c9c5500a3149c5500"
    "0fbf054e9c5500a3189c5500474383fb04728c893d249c55008974241c61c36089c683c8ffe81effffffa1249c550039"
    "f07d0289f0a32cf5540061c38b4718eb038b471c85c07e03894608e941eaeaffbe7f945500eb05be9194550089df8a06"
    "8807464784c075f6e9291fecff7d0c3d080040807405e9f8b1f4ffe9cab0f4ff60e81c01000085c0742c8b5c24248b7c"
    "24288b6c242c68009d550055576827945500536828945500ff15289c550085c00f95c00fb6c08944241c61c360e8e000"
    "000085c0746c8b5c242468009d55006a1f68609c55006827945500536828945500ff15289c550085c07447be609c5500"
    "31c031db31ff803e20750346ebf8803e2d750243460fb60e83e93083f90977096bc00a01c84746ebec85ff741385db74"
    "02f7d88b4c24288901b801000000eb0231c08944241c61c360e86400000085c0745a8b442428bf609c550085c07906c6"
    "072d47f7d8be7f9c5500c60600b90a00000031d2f7f180c2304e881685c075f28a068807464784c075f68b5c24246800"
    "9d550068609c5500536828945500ff152c9c550085c00f95c00fb6c08944241c61c3833d309c5500000f858500000068"
    "0401000068009d55006a00ff1560204c0085c07475be009d550089f78a0684c07409463c5c75f589f7ebf1be31945500"
    "8a068807464784c075f6683e945500ff1580214c0085c0744189c3684b94550053ff1570204c00a3289c550068649455"
    "0053ff1570204c00a32c9c550085c07419833d289c5500007410c705309c550001000000b801000000c331c0c30f1f00"
    "001000200040008000010002000004000800010002002000100040008000669079cd11388180803b58496e7075744765"
    "745374617465000053657474696e67730072656769737472792e696e69006b65726e656c33322e646c6c004765745072"
    "697661746550726f66696c65537472696e67410057726974655072697661746550726f66696c65537472696e6741004a"
    "4f592052494748542054524947474552004a4f59204c454654205452494747455200662e0f1f8400000000000f1f4000"
    "78696e707574315f342e646c6c00669078696e707574315f332e646c6c00669078696e707574395f315f302e646c6c00")
SYM = {"joyread": 0x000, "setcount": 0x1cf, "slider0": 0x1ec, "slider1": 0x1f1, "name12": 0x200, "name13": 0x207,
       "cdplay": 0x21d, "regstr": 0x230, "regget": 0x26c, "regset": 0x2e8}   # labels of caves.s
def C(name): return CAVE_VA + SYM[name]

def build():
    """(va, old bytes, new bytes) for every patch site."""
    e = []
    # nocd: "sub esp, 0x108" at the CD search's entry -> "mov eax, 1; ret"; its starting CD root "d:\" -> ".\"
    e.append((0x402f80, bytes.fromhex("81ec08010000"), bytes.fromhex("b801000000c3")))
    e.append((0x51661c, b"d:\\\0", b".\\\0\0"))
    # cdinstall: "call 0x43c080" (read "CDInstall") -> "mov eax, 1"; "mov edi, [esp+8]" (its value) -> "xor edi, edi"
    e.append((0x43c1ac, rel32(0x43c1ac, 0x43c080, 0xe8), bytes.fromhex("b801000000")))
    e.append((0x43c1bc, bytes.fromhex("8b7c2408"), bytes.fromhex("31ff9090")))
    # noreg: the three registry helpers' first bytes -> jmp regstr / regget / regset
    e.append((0x43c000, bytes.fromhex("518d442400"), rel32(0x43c000, C("regstr"), 0xe9)))
    e.append((0x43c080, bytes.fromhex("83ec088d4424"), rel32(0x43c080, C("regget"), 0xe9) + b"\x90"))
    e.append((0x43c100, bytes.fromhex("518d442400"), rel32(0x43c100, C("regset"), 0xe9)))
    # pad: the pump's "call 0x447a60" -> call joyread; "mov [0x54f52c], eax" (joystick count) -> call setcount
    e.append((0x446fda, rel32(0x446fda, 0x447a60, 0xe8), rel32(0x446fda, C("joyread"), 0xe8)))
    e.append((0x446ccf, bytes.fromhex("a32cf55400"), rel32(0x446ccf, C("setcount"), 0xe8)))
    # sliders: jump table entries 12 and 13 (0x407c41 = nothing) -> slider0, slider1
    e.append((0x407cb8 + 4 * 12, struct.pack("<II", 0x407c41, 0x407c41), struct.pack("<II", C("slider0"), C("slider1"))))
    # sliders: the Controls screen's name table (0x41b1a0) entries 12 and 13 (0x41b146 = no name) -> name12, name13
    e.append((0x41b1a0 + 4 * 12, struct.pack("<II", 0x41b146, 0x41b146), struct.pack("<II", C("name12"), C("name13"))))
    # cdplay: the CD player's Play, "jl 0x4a4423" after its status check -> jmp cdplay; nop
    e.append((0x4a42f4, bytes.fromhex("0f8c29010000"), rel32(0x4a42f4, C("cdplay"), 0xe9) + b"\x90"))
    # nopal (Dege): "jne 0x46c33e" -> "jne 0x46c394" for paletted texture formats
    e.append((0x46c335, bytes.fromhex("7507"), bytes.fromhex("755d")))
    # nopointer: "call 0x416320" (draw the menu pointer) -> 5-byte nop
    e.append((0x415bf5, rel32(0x415bf5, 0x416320, 0xe8), bytes.fromhex("0f1f440000")))
    # nocursor: "call [LoadCursorA]" -> "add esp, 8; xor eax, eax; nop" (hCursor = NULL)
    e.append((0x447df0, bytes.fromhex("ff15f0214c00"), bytes.fromhex("83c40831c090")))
    return e

def add_section(data):
    lfanew = struct.unpack_from("<I", data, 0x3c)[0]
    nsec = struct.unpack_from("<H", data, lfanew + 6)[0]
    optsize = struct.unpack_from("<H", data, lfanew + 20)[0]
    sh = lfanew + 24 + optsize + 40 * nsec
    if nsec != 6 or sh != 0x2e8 or any(data[sh:sh + 40]) or len(data) != SECT_OFF:
        sys.exit("unexpected PE header; nothing written")
    struct.pack_into("<8sIIIIIIHHI", data, sh, b".rdeck", SECT_SIZE, SECT_RVA, SECT_SIZE, SECT_OFF, 0, 0, 0, 0,
                     0xE0000060)       # code | initialised data | execute | read | write
    struct.pack_into("<H", data, lfanew + 6, nsec + 1)
    chars = struct.unpack_from("<H", data, lfanew + 22)[0]
    struct.pack_into("<H", data, lfanew + 22, chars | 1)     # IMAGE_FILE_RELOCS_STRIPPED (already set)
    if struct.unpack_from("<I", data, lfanew + 24 + 56)[0] != SECT_RVA: sys.exit("unexpected SizeOfImage")
    struct.pack_into("<I", data, lfanew + 24 + 56, SECT_RVA + SECT_SIZE)
    data += CAVE + bytes(SECT_SIZE - len(CAVE))

def elf_text(path):                    # .text bytes and label offsets of an i386 ELF object (no relocations)
    d = open(path, "rb").read()
    shoff = struct.unpack_from("<I", d, 0x20)[0]; shentsize, shnum, shstrndx = struct.unpack_from("<HHH", d, 0x2e)
    secs = [struct.unpack_from("<10I", d, shoff + i * shentsize) for i in range(shnum)]
    names = [d[secs[shstrndx][4] + x[0]:].split(b"\0")[0].decode() for x in secs]
    if any(n.startswith(".rel") and x[5] for n, x in zip(names, secs)): sys.exit("caves.o has relocations")
    ti = names.index(".text"); text = d[secs[ti][4]:secs[ti][4] + secs[ti][5]]; syms = {}
    for x in secs:
        if x[1] != 2: continue                                   # SHT_SYMTAB
        strs = secs[x[6]]
        for i in range(x[5] // 16):
            nm, val, size, info, oth, shn = struct.unpack_from("<IIIBBH", d, x[4] + 16 * i)
            if shn == ti: syms[d[strs[4] + nm:].split(b"\0")[0].decode()] = val
    return text, syms

ENTRIES = ("joyread", "setcount", "slider0", "slider1", "name12", "name13", "cdplay", "regstr", "regget", "regset")
def check_caves():
    with tempfile.TemporaryDirectory() as t:
        o = os.path.join(t, "caves.o")
        subprocess.run(["clang", "-target", "i386-pc-linux-gnu", "-c", os.path.join(HERE, "caves.s"), "-o", o], check=True)
        text, syms = elf_text(o)
    ok = text == CAVE and all(syms.get(k) == SYM.get(k) for k in ENTRIES)
    print("caves.s matches CAVE" if ok else "caves.s differs from CAVE / SYM: update patch_exe.py")
    if not ok:
        print("CAVE =", text.hex()); print("SYM =", {k: hex(syms[k]) for k in ENTRIES})
    return ok

def patch(data, label="SaerPC.exe"):
    """Returns the patched exe; exits on any unexpected byte."""
    data = bytearray(data)
    if len(data) != SIZE or hashlib.md5(data).hexdigest() != MD5:
        sys.exit(f"{label}: not the disc's SaerPC.exe (size {SIZE}, MD5 {MD5}); nothing written")
    assert 0 < len(CAVE) < 0xc00, "CAVE empty or running into the variables at 0x559c00"
    edits = build()
    for va, old, new in edits:
        off = T(va)
        if bytes(data[off:off + len(old)]) != old or len(old) != len(new):
            sys.exit(f"unexpected bytes at VA {va:#x}; nothing written")
    for va, old, new in edits:
        data[T(va):T(va) + len(new)] = new
    add_section(data)
    print(f"  rdeck nocd cdinstall noreg pad sliders cdplay nopal nopointer nocursor ({len(edits)} edits)")
    return bytes(data)

def main(src, dst):
    data = patch(open(src, "rb").read(), src)
    tmp = dst + ".tmp"
    open(tmp, "wb").write(data)
    os.replace(tmp, dst)
    print(f"{dst}: MD5 {hashlib.md5(data).hexdigest()}")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--check-caves": sys.exit(0 if check_caves() else 1)
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
