from pathlib import Path
from PIL import Image,ImageDraw
b=Path('霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes()
def glyph(c):
 base,offset=(0xfd000,c-0x841e) if c>=0x841e else (0x5a000,c-0x831e) if c>=0x831e else (0x55896,c-0x8140)
 return b[base+offset*32:base+offset*32+32]
for mode in range(2):
 im=Image.new('RGB',(10*140,36*50),'white');d=ImageDraw.Draw(im)
 for i in range(352):
  x=i%10*140;y=i//10*50;d.text((x,y),str(i),fill='black')
  raw=b[0x4c8d4+i*16:0x4c8d4+i*16+6]
  for n in range(3):
   c=int.from_bytes(raw[n*2:n*2+2],'big')
   if c==0:break
   data=glyph(c)
   for t in range(4):
    tx,ty=(t%2,t//2) if mode==0 else (t//2,t%2)
    for row in range(8):
     for col in range(8):
      if data[t*8+row]&(128>>col):d.rectangle((x+30+n*34+(tx*8+col)*2,y+(ty*8+row)*2,x+31+n*34+(tx*8+col)*2,y+1+(ty*8+row)*2),fill='black')
 im.save(f'.rea_tmp/name_names_{mode}.png')
