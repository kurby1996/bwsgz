from pathlib import Path
from capstone import *
from collections import Counter
r=Path(r'霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes()
c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000); c.skipdata=True
out=[]
for i in c.disasm(r[0x200:0x50000],0x200):
 if '$ff' in i.op_str or '$20' in i.op_str or (i.mnemonic.startswith('mulu') and '#' in i.op_str): out.append(f'{i.address:06x} {i.bytes.hex():16} {i.mnemonic:12} {i.op_str}')
Path('.rea_tmp/layout_refs.txt').write_text('\n'.join(out))
print('\n'.join(out[:180]))
