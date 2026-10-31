# Suzuki Alstare Extreme Racing (SaerPC.exe, the disc's exe, 1,179,648 bytes, linked 17 Apr 2000, MSVC; Criterion
# Studios / Ubi Soft, version 1.00.000): new code for patch_exe.py. It goes into a section patch_exe.py adds to the
# exe, ".rdeck" at VA 0x559000 (file offset 0x120000, the end of the file, 0x1000 bytes, readable / writable /
# executable): this code from 0x559000, its variables from 0x559c00 (zero when the exe loads). The exe always loads
# at its 0x400000 base (no relocations, "relocations stripped"), so absolute addresses are used throughout.
#
# Assembled with Apple clang (integrated assembler):
#   clang -target i386-pc-linux-gnu -c caves.s -o caves.o
# patch_exe.py carries the resulting bytes (CAVE) and checks them against this file when clang is around
# (patch_exe.py --check-caves). docs/TECHNICAL.md explains each routine.
#
# Taken from Redline Racer's caves.s (the same Criterion engine, 1998): readpad (now: the n-th connected XInput
# pad, and how many there are), axisf, trigf, the joyfill idea. New here: the registry replaced by an ini file
# (regstr / regget / regset), the joystick count (setcount), the two trigger "sliders" in the race controls
# (slider0 / slider1) and their names on the Controls screen (name12 / name13).
#
# Lesson kept from Speedster (23 Oct 2026): never keep a value in ecx / edx across an API call (Proton's
# timeGetTime and friends change them). Every routine here saves what it uses with pushad / popad, and keeps
# values across API calls only in ebx / esi / edi / ebp or memory.
.intel_syntax noprefix
.set BASE, 0x559000

# imports used (IAT slots of SaerPC.exe)
.set GetModuleFileNameA, 0x4c2060
.set LoadLibraryA,       0x4c206c
.set GetProcAddress,     0x4c2070
.set GetModuleHandleA,   0x4c2180

# game
.set JOYREAD,  0x447a60              # int JoyRead(int device, JOYSTATE *out): the DirectInput joystick read (Poll +
                                     #   GetDeviceState(DIJOYSTATE) -> X Y Z Rx Ry Rz floats -1..1, 2 sliders 0..1,
                                     #   20 button bits); device 1.. = the joysticks DirectInput listed
.set JOYCOUNT, 0x54f52c              # joysticks the input pump reads every frame (devices 1..JOYCOUNT)
.set CTLDONE,  0x407c41              # the race controls loop (0x407920): "next control"
.set CDPLAYOK, 0x4a42fa              # the CD player's Play (0x4a42c0): after its status check
.set CDPLAYERR, 0x4a4423             #   ... and its error return
.set NAMEDONE, 0x41b146              # the binding-name function (0x41a8d0): its end (trims a trailing CR, returns)

# our variables (.rdeck from 0x559c00, zero at load)
.set V,       BASE + 0xc00
.set XGS,     V + 0x00               # XInputGetState (0 = no XInput DLL)
.set XINIT,   V + 0x04               # 1 once readpad has looked for XInput
.set PB,      V + 0x08               # the pad readpad last took: XInput wButtons (DPAD_UP 1, DOWN 2, LEFT 4, RIGHT 8,
.set PLX,     V + 0x0c               #   START 0x10, BACK 0x20, L3 0x40, R3 0x80, LB 0x100, RB 0x200, A 0x1000,
.set PLY,     V + 0x10               #   B 0x2000, X 0x4000, Y 0x8000); left stick X / Y (signed, up +)
.set PRX,     V + 0x14               #   right stick X / Y
.set PRY,     V + 0x18
.set PLT,     V + 0x1c               #   left / right trigger 0..255
.set PRT,     V + 0x20
.set XCOUNT,  V + 0x24               # XInput pads connected at the last look
.set GPPS,    V + 0x28               # GetPrivateProfileStringA
.set WPPS,    V + 0x2c               # WritePrivateProfileStringA
.set INIOK,   V + 0x30               # 1 once iniinit has run (and found both)
.set XS,      V + 0x40               # an XINPUT_STATE (16 bytes)
.set NUMBUF,  V + 0x60               # a number as text (32 bytes)
.set INIPATH, V + 0x100              # <the exe's folder>\registry.ini (0x110 bytes)

.set DZ,      4000                   # stick dead zone (of 32767): about 12 %
.set TDZ,     8                      # trigger dead zone (of 255)

.macro PUSHI v                       # push imm32 (clang's intel syntax would make "push offset" 16-bit)
  .byte 0x68
  .long \v
.endm

.text
start:

# ---------------------------------------------------------------------------------------------------------------
# joyread (patch pad): the input pump (0x446fc0, every frame: menus, races, the logos) reads joystick n = 1..JOYCOUNT
# with "push out; push n; call JoyRead" (0x446fda) and hands the reading to the current input handler as event 0x16.
# The call now comes here; same arguments (cdecl), same result (eax 1 = a reading). Joystick n is the n-th connected
# XInput pad, written by joyfill; when XInput pads are connected but fewer than n, no reading (so DirectInput's own
# copy of the same pad is not read twice); with no XInput pad at all, the game's own DirectInput read runs
# (jmp JOYREAD: the stack is as the game left it).
joyread:
  pushad
  mov esi, dword ptr [esp + 0x28]    # JOYSTATE * (pushad 0x20, return address, device, out)
  mov eax, dword ptr [esp + 0x24]
  dec eax                            # the pad's place among the connected ones
  call readpad
  test eax, eax
  jnz 1f
  cmp dword ptr [XCOUNT], 0
  jne 2f
  popad
  .byte 0xe9                         # jmp JOYREAD: the game's own read
  .long JOYREAD - (BASE + (3f - start))
3:
2:
  popad
  xor eax, eax
  ret
1:
  call joyfill
  popad
  mov eax, 1
  ret

# joyfill: esi = the game's JOYSTATE. From readpad's reading:
#   +0x00 X, +0x04 Y  the left stick (-1..1, DirectInput sense: right / down positive), dead zone DZ
#   +0x08 Z           0 (the game binds no Z)
#   +0x0c Rx, +0x10 Ry  the right stick (the game binds neither)
#   +0x14 Rz          0
#   +0x18 slider 1    RT, 0..1   } separate analogue triggers (DirectInput puts an Xbox pad's triggers on one
#   +0x1c slider 2    LT, 0..1   } shared axis under Proton: both held = neither); bound by patch sliders
#   +0x20 buttons     game button n (binding parameter 14 + n) = btnmap[n]: 0 A, 1 B, 2 X, 3 Y, 4 LB, 5 RB,
#                     6 none, 7-10 D-pad left / right / up / down, 11 View, 12 Start, 13 L3, 14 R3.
#                     The menus (0x414550) take button 0 as "choose", 1 as "back", 7-10 as the four directions.
joyfill:
  mov ebx, dword ptr [PB]
  mov eax, dword ptr [PLX]
  call axisf
  fstp dword ptr [esi]
  mov eax, dword ptr [PLY]
  call axisf
  fchs                               # XInput up = +, DirectInput up = -
  fstp dword ptr [esi + 4]
  mov dword ptr [esi + 8], 0
  mov eax, dword ptr [PRX]
  call axisf
  fstp dword ptr [esi + 0xc]
  mov eax, dword ptr [PRY]
  call axisf
  fchs
  fstp dword ptr [esi + 0x10]
  mov dword ptr [esi + 0x14], 0
  mov eax, dword ptr [PRT]
  call trigf
  fstp dword ptr [esi + 0x18]
  mov eax, dword ptr [PLT]
  call trigf
  fstp dword ptr [esi + 0x1c]
  xor ecx, ecx                       # buttons
  .byte 0xbf                         # mov edi, btnmap
  .long A_BTNMAP
  xor edx, edx
5:
  movzx eax, word ptr [edi + edx*2]
  test ebx, eax
  jz 6f
  bts ecx, edx
6:
  inc edx
  cmp edx, 15
  jb 5b
  mov dword ptr [esi + 0x20], ecx
  ret

# axisf: eax = a stick axis (-32768..32767) -> st(0) = -1..1, 0 inside the dead zone DZ and scaled from its edge
# (no jump at the edge). Changes eax, ecx, edx.
axisf:
  mov ecx, eax
  cdq
  xor eax, edx
  sub eax, edx                       # |value|
  sub eax, DZ
  jg 1f
  fldz
  ret
1:
  cmp eax, 32767 - DZ
  jle 2f
  mov eax, 32767 - DZ
2:
  push eax
  fild dword ptr [esp]
  fmul dword ptr [A_AXSCALE]
  pop eax
  test ecx, ecx
  jns 3f
  fchs
3:
  ret

# trigf: eax = a trigger (0..255) -> st(0) = 0..1, 0 below TDZ. Changes eax.
trigf:
  cmp eax, TDZ
  jge 1f
  fldz
  ret
1:
  push eax
  fild dword ptr [esp]
  fmul dword ptr [A_TRSCALE]
  pop eax
  ret

# ---------------------------------------------------------------------------------------------------------------
# readpad: eax = n -> the n-th connected XInput pad (0 = the first; pads 0..3 in XInput order) into PB / PLX / PLY /
# PRX / PRY / PLT / PRT; XCOUNT = how many are connected. The first call looks for XInputGetState in xinput1_4.dll,
# else xinput1_3.dll, else xinput9_1_0.dll (Proton has all three; Windows 8+ has 1_4 and 9_1_0; the exe imports
# none of them). Returns eax = 1 with a reading, 0 without (no XInput, fewer pads). Keeps every other register.
readpad:
  pushad
  mov ebp, eax
  cmp dword ptr [XINIT], 0
  jne 10f
  mov dword ptr [XINIT], 1
  .byte 0xbe                         # mov esi, the three names (16 bytes each)
  .long A_XINPUT
  mov ebx, 3
2:
  push esi
  call dword ptr [LoadLibraryA]
  test eax, eax
  jz 3f
  PUSHI BASE + (s_xgs - start)
  push eax
  call dword ptr [GetProcAddress]
  test eax, eax
  jz 3f
  mov dword ptr [XGS], eax
  jmp 10f
3:
  add esi, 16
  dec ebx
  jnz 2b
10:
  xor esi, esi                       # 1 = the pad was found
  xor edi, edi                       # connected pads so far
  cmp dword ptr [XGS], 0
  je 20f
  xor ebx, ebx                       # XInput user index
11:
  PUSHI XS
  push ebx
  call dword ptr [XGS]
  test eax, eax
  jnz 13f                            # not connected
  cmp edi, ebp
  jne 12f
  mov esi, 1
  movzx eax, word ptr [XS + 4]
  mov dword ptr [PB], eax
  movzx eax, byte ptr [XS + 6]
  mov dword ptr [PLT], eax
  movzx eax, byte ptr [XS + 7]
  mov dword ptr [PRT], eax
  movsx eax, word ptr [XS + 8]
  mov dword ptr [PLX], eax
  movsx eax, word ptr [XS + 10]
  mov dword ptr [PLY], eax
  movsx eax, word ptr [XS + 12]
  mov dword ptr [PRX], eax
  movsx eax, word ptr [XS + 14]
  mov dword ptr [PRY], eax
12:
  inc edi
13:
  inc ebx
  cmp ebx, 4
  jb 11b
20:
  mov dword ptr [XCOUNT], edi
  mov dword ptr [esp + 0x1c], esi    # eax (pushad's slot)
  popad
  ret

# ---------------------------------------------------------------------------------------------------------------
# setcount (patch pad): after DirectInput's set-up the skeleton stores how many joysticks it found
# ("mov [JOYCOUNT], eax", 0x446ccf); the input pump reads that many every frame. That store comes here: the
# DirectInput count, or the number of connected XInput pads when that is more (a pad Proton's DirectInput did not
# list still works). Changes nothing else (the code after it sets eax itself).
setcount:
  pushad
  mov esi, eax
  or eax, -1                         # no pad wanted: only count them
  call readpad
  mov eax, dword ptr [XCOUNT]
  cmp eax, esi
  jge 1f
  mov eax, esi
1:
  mov dword ptr [JOYCOUNT], eax
  popad
  ret

# ---------------------------------------------------------------------------------------------------------------
# slider0 / slider1 (patch sliders): the race controls (0x407920) read a joystick binding by its parameter through a
# jump table (0x407cb8): 0-3 the stick's four directions, 14-29 buttons 0-15. The Controls screen also binds the
# two DirectInput sliders (parameters 12 and 13, 0x4105b2) but the table sent both to "nothing". Entries 12 and 13
# now come here: the control's value (+8) = the slider (0..1) when it is above 0, as the stick directions do.
# edi = the joystick's reading, esi = the control; eax is free.
slider0:
  mov eax, dword ptr [edi + 0x18]
  jmp 1f
slider1:
  mov eax, dword ptr [edi + 0x1c]
1:
  test eax, eax                      # a float above 0 is a positive integer
  jle 2f
  mov dword ptr [esi + 8], eax
2:
  .byte 0xe9                         # jmp CTLDONE
  .long CTLDONE - (BASE + (3f - start))
3:

# name12 / name13 (patch sliders): the Controls screen names a binding with 0x41a8d0 (a joystick parameter through
# the jump table 0x41b1a0: "JOY LEFT" ... from common\strings.txt, "JOY BUTTON n"); parameters 12 and 13 had no
# name (the screen would show whatever its buffer held). Now "JOY RIGHT TRIGGER" / "JOY LEFT TRIGGER" (what they
# are with an XInput pad), copied to the output buffer (ebx); then the function's own end (NAMEDONE). esi, edi,
# eax are free there.
name12:
  .byte 0xbe                         # mov esi, "JOY RIGHT TRIGGER"
  .long BASE + (s_rt - start)
  jmp 1f
name13:
  .byte 0xbe                         # mov esi, "JOY LEFT TRIGGER"
  .long BASE + (s_lt - start)
1:
  mov edi, ebx
2:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  inc esi
  inc edi
  test al, al
  jnz 2b
  .byte 0xe9                         # jmp NAMEDONE
  .long NAMEDONE - (BASE + (3f - start))
3:

# ---------------------------------------------------------------------------------------------------------------
# cdplay (patch cdplay): Criterion's Dive CD player (the "Dive.WindowsCDAudioRedbook" component, vtable
# 0x4e33a0) starts a track in two steps: Seek (0x4a46f0: MCI_SEEK to the track) then Play (0x4a42c0: MCI_PLAY from
# that track to the next). Both first call its status method (0x4a4840), which ends by asking the type of the
# *current* track (MCI_STATUS_CURRENT_TRACK, 0x4a47e0, then MCI_CDA_STATUS_TYPE_TRACK) and returns 0x80400008 when it
# is not an audio track. A real drive reports the track it was just sought to; ogg-winmm reports track 0 until
# something plays, so the type is "other". Seek already takes 0x80400008 as fine; Play took it as an error and
# returned before MCI_PLAY: no music at all (seen on the Deck, 24 Oct 2026: seek, status, no play). Play's
# "test eax, eax; jl error" (0x4a42f4) now comes here: 0x80400008 goes on as Seek does, other errors still return.
cdplay:
  jge 1f                             # the flags of Play's "test eax, eax"
  cmp eax, 0x80400008
  je 1f
  .byte 0xe9                         # jmp CDPLAYERR
  .long CDPLAYERR - (BASE + (2f - start))
2:
1:
  .byte 0xe9                         # jmp CDPLAYOK
  .long CDPLAYOK - (BASE + (3f - start))
3:

# ---------------------------------------------------------------------------------------------------------------
# The registry (patch noreg). The game keeps its settings in HKLM\Software\Criterion Studios\Suzuki Alstare Extreme
# Racing\1.00.000 through three helpers: 0x43c000 (read a string), 0x43c080 (read a DWORD), 0x43c100 (write a
# DWORD; it opens the key, never creates it, so without the installer nothing is ever saved). Each now jumps here
# and uses <the exe's folder>\registry.ini, section [Settings], one "name=value" line per registry value (DWORDs as
# signed decimal numbers). Same arguments (cdecl) and results (eax 1 = done, 0 = not there).
#
# regstr(name, buf, size): the string, as RegQueryValueExA would give it (0x43c000)
regstr:
  pushad
  call iniinit
  test eax, eax
  jz 9f
  mov ebx, dword ptr [esp + 0x24]
  mov edi, dword ptr [esp + 0x28]
  mov ebp, dword ptr [esp + 0x2c]
  PUSHI INIPATH
  push ebp
  push edi
  PUSHI BASE + (s_empty - start)
  push ebx
  PUSHI BASE + (s_section - start)
  call dword ptr [GPPS]
  test eax, eax
  setnz al
  movzx eax, al
9:
  mov dword ptr [esp + 0x1c], eax
  popad
  ret

# regget(name, int *out): the number (0x43c080)
regget:
  pushad
  call iniinit
  test eax, eax
  jz 9f
  mov ebx, dword ptr [esp + 0x24]
  PUSHI INIPATH
  push 31
  PUSHI NUMBUF
  PUSHI BASE + (s_empty - start)
  push ebx
  PUSHI BASE + (s_section - start)
  call dword ptr [GPPS]
  test eax, eax
  jz 9f
  .byte 0xbe                         # mov esi, NUMBUF
  .long NUMBUF
  xor eax, eax                       # value
  xor ebx, ebx                       # 1 = negative
  xor edi, edi                       # digits seen
1:
  cmp byte ptr [esi], ' '
  jne 2f
  inc esi
  jmp 1b
2:
  cmp byte ptr [esi], '-'
  jne 3f
  inc ebx
  inc esi
3:
  movzx ecx, byte ptr [esi]
  sub ecx, '0'
  cmp ecx, 9
  ja 4f
  imul eax, eax, 10
  add eax, ecx
  inc edi
  inc esi
  jmp 3b
4:
  test edi, edi
  jz 8f
  test ebx, ebx
  jz 5f
  neg eax
5:
  mov ecx, dword ptr [esp + 0x28]
  mov dword ptr [ecx], eax
  mov eax, 1
  jmp 9f
8:
  xor eax, eax
9:
  mov dword ptr [esp + 0x1c], eax
  popad
  ret

# regset(name, int value): write it (0x43c100)
regset:
  pushad
  call iniinit
  test eax, eax
  jz 9f
  mov eax, dword ptr [esp + 0x28]
  .byte 0xbf                         # mov edi, NUMBUF
  .long NUMBUF
  test eax, eax
  jns 1f
  mov byte ptr [edi], '-'
  inc edi
  neg eax
1:
  .byte 0xbe                         # mov esi, NUMBUF + 31 (the digits are built backwards from there)
  .long NUMBUF + 31
  mov byte ptr [esi], 0
  mov ecx, 10
2:
  xor edx, edx
  div ecx
  add dl, '0'
  dec esi
  mov byte ptr [esi], dl
  test eax, eax
  jnz 2b
3:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  inc esi
  inc edi
  test al, al
  jnz 3b
  mov ebx, dword ptr [esp + 0x24]
  PUSHI INIPATH
  PUSHI NUMBUF
  push ebx
  PUSHI BASE + (s_section - start)
  call dword ptr [WPPS]
  test eax, eax
  setnz al
  movzx eax, al
9:
  mov dword ptr [esp + 0x1c], eax
  popad
  ret

# iniinit: the first time, INIPATH = the exe's folder + "registry.ini" (GetModuleFileNameA) and
# Get / WritePrivateProfileStringA from kernel32. Returns eax = 1 when both are there. Changes every register.
iniinit:
  cmp dword ptr [INIOK], 0
  jne 8f
  push 0x104
  PUSHI INIPATH
  push 0
  call dword ptr [GetModuleFileNameA]
  test eax, eax
  jz 9f
  .byte 0xbe                         # mov esi, INIPATH
  .long INIPATH
  mov edi, esi                       # just after the last '\'
1:
  mov al, byte ptr [esi]
  test al, al
  jz 2f
  inc esi
  cmp al, '\\'
  jne 1b
  mov edi, esi
  jmp 1b
2:
  .byte 0xbe                         # mov esi, "registry.ini"
  .long BASE + (s_ininame - start)
3:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  inc esi
  inc edi
  test al, al
  jnz 3b
  PUSHI BASE + (s_kernel32 - start)
  call dword ptr [GetModuleHandleA]
  test eax, eax
  jz 9f
  mov ebx, eax
  PUSHI BASE + (s_gpps - start)
  push ebx
  call dword ptr [GetProcAddress]
  mov dword ptr [GPPS], eax
  PUSHI BASE + (s_wpps - start)
  push ebx
  call dword ptr [GetProcAddress]
  mov dword ptr [WPPS], eax
  test eax, eax
  jz 9f
  cmp dword ptr [GPPS], 0
  je 9f
  mov dword ptr [INIOK], 1
8:
  mov eax, 1
  ret
9:
  xor eax, eax
  ret

# ---------------------------------------------------------------------------------------------------------------
  .p2align 2
btnmap:    .short 0x1000, 0x2000, 0x4000, 0x8000, 0x0100, 0x0200, 0x0000, 0x0004
           .short 0x0008, 0x0001, 0x0002, 0x0020, 0x0010, 0x0040, 0x0080
                                     # game buttons 0-14 (A B X Y LB RB - left right up down View Start L3 R3)
                                     # as XInput bits
  .p2align 2
f_axscale: .long 0x3811cd79          # 1 / (32767 - DZ) = 1 / 28767
f_trscale: .long 0x3b808081          # 1 / 255
s_xgs:     .asciz "XInputGetState"
s_empty:   .asciz ""
s_section: .asciz "Settings"
s_ininame: .asciz "registry.ini"
s_kernel32: .asciz "kernel32.dll"
s_gpps:    .asciz "GetPrivateProfileStringA"
s_wpps:    .asciz "WritePrivateProfileStringA"
s_rt:      .asciz "JOY RIGHT TRIGGER"
s_lt:      .asciz "JOY LEFT TRIGGER"
  .p2align 4
s_xinput:  .asciz "xinput1_4.dll"
  .p2align 4
           .asciz "xinput1_3.dll"
  .p2align 4
           .asciz "xinput9_1_0.dll"
.set A_AXSCALE, BASE + (f_axscale - start)
.set A_TRSCALE, BASE + (f_trscale - start)
.set A_XINPUT, BASE + (s_xinput - start)
.set A_BTNMAP, BASE + (btnmap - start)
