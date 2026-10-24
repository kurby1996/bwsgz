from pathlib import Path
from capstone import *
b=Path('霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes();c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);c.skipdata=True
for i in c.disasm(b[:0x40000],0):
 if any(s in i.op_str for s in ['$d9','$da','$db','$dc','$dd','$de','$df','$e0','$e1','$e2','$e3','$e4','$53','$54','$55','$56']):
  if '#' in i.op_str or '.l' in i.op_str:print(f'{i.address:06x} {i.mnemonic:12} {i.op_str}')
