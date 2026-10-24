import socket, time
from pathlib import Path
s=socket.create_connection(('127.0.0.1',1234),3)
s.settimeout(5)
def cmd(c):
    b=c.encode(); s.sendall(b'$'+b+b'#'+f'{sum(b)%256:02x}'.encode())
    out=b''
    while b'#' not in out or len(out.split(b'#')[-1])<2: out+=s.recv(8192)
    s.sendall(b'+')
    return out[out.index(b'$')+1:out.index(b'#')]
print('stop',cmd('?'))
print('regs',cmd('g'))
ram=bytearray()
for off in range(0,65536,512):ram.extend(bytes.fromhex(cmd(f'm{0xff0000+off:x},200').decode()))
Path('.rea_tmp/live_ram.bin').write_bytes(ram)
print('RAM saved',ram[0x1052:0x1052+48].hex())
print('continue')
s.sendall(b'$c#63');time.sleep(.2);s.close()
