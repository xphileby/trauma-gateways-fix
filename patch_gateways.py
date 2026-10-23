#!/usr/bin/env python3
"""Make Trauma's demo "Gateways" (Assembly'98, GATEWAYS.EXE) run in true colour with sound on a modern real-DOS PC.

Two bytes are changed in the DOS/4GW (LE) executable:

1. The VBE setup code maps the whole video memory with DPMI 0800h (VbeInfo.TotalMemory << 16 = 256 MB on a
   GeForce 7800), ignores the failure, and then draws to the raw physical LFB address -> page fault under every
   paging host (EMM386 / JemmEx / QEMM), i.e. in every setup that also gives the demo sound.
   `shl edx,10h` -> `shl edx,9` maps VRAM / 128 (2 MB on a 256 MB card; a 320x200x32 frame is 250 KB).
2. The closing effect walks an index table from position eax/2 downward. On the last frame eax == edx and it reads
   one entry past the end -> garbage index -> page fault right at the end. `jg` -> `jge` at the comparison.

Usage:  python3 patch_gateways.py GATEWAYS.EXE [OUTPUT]     (default: GATEWAYP.EXE next to the input)
"""
import os
import struct
import sys


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) == 3 else os.path.join(os.path.dirname(src) or '.', 'GATEWAYP.EXE')
    b = bytearray(open(src, 'rb').read())
    le = struct.unpack_from('<I', b, 0x3c)[0]
    if b[le:le + 2] != b'LE':
        raise SystemExit('not a DOS/4GW LE executable')
    datapg = struct.unpack_from('<I', b, le + 0x80)[0]
    objtab = struct.unpack_from('<I', b, le + 0x40)[0]
    base = struct.unpack_from('<I', b, le + objtab + 4)[0]
    first_page = struct.unpack_from('<I', b, le + objtab + 12)[0]
    at = lambda addr: datapg + (first_page - 1) * 4096 + (addr - base)   # object 1 address -> file offset

    done = []
    o = at(0x4469f)                       # xor edx,edx / mov dx,[TotalMemory] / shl edx,10h / call map_physical
    if b[o:o + 3] == b'\xc1\xe2\x10' and b[o + 3] == 0xe8:
        b[o + 2] = 9; done.append(f'file {o + 2:#x}: shl edx,10h -> shl edx,9 (map VRAM/128)')
    elif b[o:o + 3] == b'\xc1\xe2\x09':
        done.append('VRAM mapping: already patched')
    else:
        raise SystemExit(f'unexpected code at {o:#x}: {b[o:o + 4].hex()} (different GATEWAYS.EXE build?)')
    o = at(0x1afcc)                       # cmp eax,edx / jg  ->  jge
    if b[o:o + 4] == b'\x39\xd0\x0f\x8f':
        b[o + 3] = 0x8d; done.append(f'file {o + 3:#x}: jg -> jge (closing effect off-by-one)')
    elif b[o:o + 4] == b'\x39\xd0\x0f\x8d':
        done.append('closing effect: already patched')
    else:
        raise SystemExit(f'unexpected code at {o:#x}: {b[o:o + 4].hex()}')
    open(dst, 'wb').write(b)
    print('\n'.join(done) + f'\nwritten {dst}')


if __name__ == '__main__':
    main()
