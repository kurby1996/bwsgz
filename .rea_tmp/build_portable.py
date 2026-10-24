import pathlib,shutil,hashlib,json,struct
import pefile
root=pathlib.Path(__file__).resolve().parent.parent
src=root/'.rea_tmp/extracted/XiaoJi'
out=root/'XiaoJi-NoActivation'
out.mkdir(exist_ok=True)
dst=out/'runtime'
shutil.copytree(src,dst,dirs_exist_ok=True)
p=dst/'XiaoJi.exe'; b=bytearray(p.read_bytes()); pe=pefile.PE(data=b)
patches=[]
def patch(va,expected,new,reason):
 off=pe.get_offset_from_rva(va-pe.OPTIONAL_HEADER.ImageBase)
 assert b[off:off+len(expected)]==expected,hex(va)
 old=bytes(b[off:off+len(new)]); b[off:off+len(new)]=new
 patches.append(dict(va=hex(va),offset=hex(off),before=old.hex(),after=new.hex(),reason=reason))
patch(0x14013b070,bytes.fromhex('48895c2410'),bytes.fromhex('b801000000c3'),'Local activation predicate returns true')
patch(0x14013aa70,bytes.fromhex('48895c2410'),bytes.fromhex('c741180100000048b8005764860000000048894110c3'),'Local status and expiry, no remote receipt refresh')
old=b"level='requireAdministrator'"
new=b"level='asInvoker'"+b' '*(len(old)-len(b"level='asInvoker'"))
assert b.count(old)==1
off=b.find(old);b[off:off+len(old)]=new
patches.append(dict(offset=hex(off),before=old.decode(),after=new.decode(),reason='Portable app does not require elevation'))
p.write_bytes(b)
pe=pefile.PE(str(p)); pe.OPTIONAL_HEADER.CheckSum=pe.generate_checksum(); pe.write(str(p))
(out/'patch-manifest.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256((src/'XiaoJi.exe').read_bytes()).hexdigest(),output_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),patches=patches),indent=2),encoding='utf8')
print(out)
