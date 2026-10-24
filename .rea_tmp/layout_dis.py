from pathlib import Path
from capstone import *
import sys
r=Path(r'霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes(); c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000); c.skipdata=True
s=int(sys.argv[1],16);e=int(sys.argv[2],16)
for i in c.disasm(r[s:e],s): print(f'{i.address:06x} {i.mnemonic:12} {i.op_str}')
