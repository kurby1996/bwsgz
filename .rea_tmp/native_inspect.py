import pathlib, sys, bisect, re, json
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_MEM, X86_REG_RIP
P=pathlib.Path(__file__).parent/'extracted/XiaoJi/XiaoJi.exe'
b=P.read_bytes(); pe=pefile.PE(data=b); base=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86,CS_MODE_64); md.detail=True; md.skipdata=True
funcs=[(x.struct.BeginAddress+base,x.struct.EndAddress+base) for x in pe.DIRECTORY_ENTRY_EXCEPTION]
starts=[x[0] for x in funcs]
def func(a):
 i=bisect.bisect_right(starts,a)-1
 return funcs[i] if i>=0 and a<funcs[i][1] else (a,a+200)
def dis(a,end=None):
 if end is None:a,end=func(a)
 off=pe.get_offset_from_rva(a-base)
 for i in md.disasm(b[off:off+end-a],a):print(f'{i.address:x} {i.bytes.hex():20} {i.mnemonic:8} {i.op_str}')
if len(sys.argv)<2:pass
elif sys.argv[1]=='calls':
 target=int(sys.argv[2],16)
 for s in pe.sections:
  if not s.Characteristics&0x20000000:continue
  for i in md.disasm(s.get_data(),base+s.VirtualAddress):
   if i.mnemonic=='call' and i.op_str==hex(target):print(hex(i.address),list(map(hex,func(i.address))))
elif sys.argv[1]=='dis':
 dis(int(sys.argv[2],16),int(sys.argv[3],16) if len(sys.argv)>3 else None)
elif sys.argv[1]=='refs':
 targets=[]
 for pat in sys.argv[2:]:
  for m in re.finditer(re.escape(pat.encode()),b):
   va=pe.get_rva_from_offset(m.start())+base; targets.append((va,pat))
 out=[]
 for s in pe.sections:
  if not s.Characteristics&0x20000000:continue
  for i in md.disasm(s.get_data(),base+s.VirtualAddress):
   if i.id==0:continue
   for o in i.operands:
    if o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP:
     a=i.address+i.size+o.mem.disp
     for va,p in targets:
      if va==a:out.append({'string':p,'address':hex(i.address),'function':list(map(hex,func(i.address)))})
 print(json.dumps(out,indent=2))
