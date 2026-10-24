# -*- coding: utf-8 -*-
"""Scan Sangokushi II MD ROM for SRAM access patterns."""
import re, sys

ROM = r"F:\AI\霸王三国志\霸王三国志-免登录版\roms\三國志II-霸王三国志.md"
rom = open(ROM, 'rb').read()

def show(pat, label, limit=40):
    print(f"=== {label} ===")
    n = 0
    for m in re.finditer(pat, rom):
        s = m.start()
        if s % 2 == 1:
            continue
        print(f"  @0x{s:06X}: {rom[s:s+8].hex(' ')}")
        n += 1
        if n >= limit:
            print("  ...")
            break
    if n == 0:
        print("  (none)")
    print()

# LEA $2000xx.L, An
show(rb'[\x41\x43\x45\x47\x49\x4b\x4d\x4f]\xf9\x00\x20', "LEA $2000xx, An")
# MOVE.B/W/L Dn -> abs.L 0x2000xx : 13/23/33 C0-CF
show(rb'[\x13\x23\x33][\xc0-\xcf]\x00\x20', "MOVE Dn -> $2000xx")
# MOVE abs.L -> Dn : 13/23/33 D0-DF
show(rb'[\x13\x23\x33][\xd0-\xdf]\x00\x20', "MOVE $2000xx -> Dn")
# MOVEA.L abs -> An / MOVE.L abs -> dn  20/22/24/26/28/2A/2C/2E 39 + addr;  20 39 00 20 ...
show(rb'[\x20\x22\x24\x26\x28\x2a\x2c\x2e]\x39\x00\x20', "MOVE.L $2000xx, An/dn")
show(rb'[\x21\x23\x25\x27\x29\x2b\x2d\x2f]\xc[\x00-\x0f]\x00\x20', "MOVEA Dn -> $2000xx")
# PEA / CLR / TST / CMPI on abs.L
show(rb'\x4f\xf9\x00\x20', "PEA $2000xx")
# generic abs.L refs anywhere
show(rb'\x00\x20\x00[\x00-\x40]', "raw '00 20 00 xx'", 60)
