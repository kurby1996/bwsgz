# -*- coding: utf-8 -*-
"""Disassemble around SRAM references in Sangokushi II MD ROM."""
from capstone import *
import sys

ROM = r"F:\AI\霸王三国志\霸王三国志-免登录版\roms\三國志II-霸王三国志.md"
rom = open(ROM, 'rb').read()
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)

SITES = [0x00C172, 0x00C1F0, 0x00DFF0, 0x0209A6, 0x020DF2]
CTX = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x60

for site in SITES:
    print(f"########## around 0x{site:06X} ##########")
    start = site - CTX
    # disassemble from start; capstone m68k linear sweep
    code = rom[start:site + CTX + 0x20]
    n = 0
    for insn in md.disasm(code, start):
        mark = " <<<" if abs(insn.address - site) < 6 else ""
        print(f"  0x{insn.address:06X}: {str(insn.bytes.hex()):<14} {insn.mnemonic} {insn.op_str}{mark}")
        n += 1
        if insn.address > site + CTX:
            break
        if n > 120:
            print("  ...")
            break
    print()
