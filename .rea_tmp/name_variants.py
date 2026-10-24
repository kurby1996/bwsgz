from pathlib import Path
from PIL import Image,ImageDraw
b=Path('霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes()
im=Image.new('RGB',(16*60,8*70),'white');d=ImageDraw.Draw(im)
for variant in range(8):
 start=0xd9000+variant//2*32
 for i in range(16):
  x=i*60;y=variant*70
  d.text((x,y),f'{start+i*128:05X}',fill='black')
  for t in range(4):
   tx,ty=(t%2,t//2) if variant%2==0 else (t//2,t%2)
   for row in range(8):
    for col in range(8):
     v=b[start+i*128+t*32+row*4+col//2];v=(v>>4 if col%2==0 else v&15)
     if v:d.rectangle((x+(tx*8+col)*2,y+14+(ty*8+row)*2,x+(tx*8+col)*2+1,y+14+(ty*8+row)*2+1),fill='black')
im.save('.rea_tmp/name_variants.png')
