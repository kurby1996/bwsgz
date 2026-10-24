from pathlib import Path
r=Path(r'霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes()
for target in [0x3eb4,0x3f14,0x688c]:
 p=bytes.fromhex('4eb9')+target.to_bytes(4,'big'); hits=[i for i in range(len(r)) if r.startswith(p,i)]
 print(hex(target),[hex(i) for i in hits[:100]])
