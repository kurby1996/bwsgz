from pathlib import Path
from capstone import *
r=Path(r'霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes();c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);c.skipdata=True
lines=[f'{i.address:06x} {i.mnemonic:12} {i.op_str}' for i in c.disasm(r[0x3500:0x41800],0x3500)]
Path('.rea_tmp/layout_all.txt').write_text('\n'.join(lines))
