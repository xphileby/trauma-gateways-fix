# trauma-gateways-fix

A two-byte patch for **Gateways** by Trauma (Assembly 1998, PC demo competition). With it, the demo runs on a modern
real-DOS PC from start to finish, in true colour and with sound.

## The problem

On a PC with a current video card (tested: GeForce 7800 GS, 256 MB), the demo fails in two ways:

- **Picture.** The 32-bit and 16-bit video modes crash right away with a DOS/4GW page fault whenever a paging memory
  manager is loaded (EMM386, JemmEx, QEMM). Sound needs one: the Sound Blaster emulation of a PCI card (Creative
  SBEINIT for the SB Live!, SBEMU, ...) depends on it. So you can have true colour without sound (bare HIMEM) or
  sound with the 256-colour fallback, but not both.
- **Exit.** Even when it runs, the demo crashes with a page fault at its very last frame, when the closing effect
  ends.

## Root cause

1. **VRAM mapping.** The VBE setup code (object 1, address 0x44696) maps the linear frame buffer with DPMI function
   0800h, asking for `VbeInfo.TotalMemory << 16` bytes, i.e. the card's entire memory. In 1998 that was 2 to 8 MB.
   Now it is hundreds of MB, and the mapping fails under a paging host. The code ignores the error and goes on to
   write to the raw physical LFB address, which is not mapped, so it page-faults.
2. **Off-by-one in the closing effect.** The effect walks an index table downward, starting at `eax/2`, and
   compares with `cmp eax,edx / jg`. On the last frame `eax == edx`, and it reads one entry past the end of the table.
   The garbage index then makes it read memory far outside the demo (CR2 around 512 MB). This goes unnoticed without
   paging, and crashes with it.

## The fix

| File offset | Original | Patched | Meaning |
|---|---|---|---|
| 0x4E8A1 | `10` (`shl edx,10h`) | `09` (`shl edx,9`) | map VRAM / 128 (2 MB on a 256 MB card; one 320x200x32 frame is 250 KB) |
| 0x251CF | `8F` (`jg`) | `8D` (`jge`) | stop the closing effect before it reads past its table |

| File | Size | MD5 |
|---|---|---|
| `GATEWAYS.EXE` (final party version) | 2932123 | `f0c75d7b9ef74ab5fd754e9b26c266ae` |
| `GATEWAYP.EXE` after the patch | 2932123 | `3a80de68087aa3c02b20d76dcb835d6a` |

As with any VRAM / 128 mapping, this needs a card with at least 32 MB of VRAM. Older cards never had the problem.

## Usage

```
python3 patch_gateways.py GATEWAYS.EXE              # writes GATEWAYP.EXE next to it, original untouched
python3 patch_gateways.py GATEWAYS.EXE OUT.EXE
```

The script locates both places through the LE object table, checks the exact bytes, and refuses to touch a
different build. Then run the patched copy:

```
GATEWAYP 0g
```

- `0` skips MIDAS's playback-speed calibration ("evil MIDAS replay speed bug" fix). With the calibration, the demo
  hangs on fast CPUs under emulated sound.
- `g` selects the 32-bit graphics mode. The other switches are listed in `GATEWAYS.TXT`.

## Tested

- Real hardware: Core 2 Extreme X6800, GeForce 7800 GS AGP (256 MB), Sound Blaster Live!.
- DOS 7.1 with JemmEx (`SB` option, EMS on) and Creative SBEINIT 5.00, DOS/4GW as bound in the executable.
- `GATEWAYP 0g` runs in 32-bit colour with MIDAS sound through the SB emulation, plays to the end, and returns to
  DOS cleanly.

Without EMS (JemmEx `NOEMS`) the demo stops with "Out of memory (about 24 megs required)". Load the memory manager
with EMS enabled.
