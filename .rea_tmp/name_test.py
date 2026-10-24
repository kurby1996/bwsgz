from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trainer.names import *

rom = Path('霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes()
all_names = names_for_rom(rom)
assert len(all_names) == 352
assert all('〔' not in n for n in all_names)
assert all_names[:3] == ['曹操', '刘备', '孙坚']
assert all_names[254:256] == ['吕翔', '诸葛亮']
assert encode_name(rom, '劉備') == encode_name(rom, '刘备')
for index, text in enumerate(all_names):
    edited = bytearray(rom)
    rename_in_rom(edited, index, text)
    assert resolve_name(edited, index) == text
    start = NAME_BASE + index * NAME_STRIDE
    assert edited[:start] == rom[:start]
    assert edited[start + NAME_BYTES:] == rom[start + NAME_BYTES:]
for text in ('', '曹操刘备', '🙂', 'A'):
    try:
        encode_name(rom, text)
    except ValueError:
        pass
    else:
        raise AssertionError(text)
assert len(glyph_bitmap(rom, 0x8397)) == 16
print('352 names decoded and renamed; preservation, bounds, unsupported glyphs, traditional aliases: PASS')
