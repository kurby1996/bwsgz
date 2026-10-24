from pathlib import Path
from PIL import Image,ImageDraw
b=Path('霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes()
for start,count in [(0xd905a,384),(0x54000,160),(0x55000,512)]:
 im=Image.new('RGB',(16*60,((count+15)//16)*58),'white');d=ImageDraw.Draw(im)
 for i in range(count):
  x=i%16*60;y=i//16*58
  d.text((x,y),f'{start+i*128:05X}',fill='black')
  for t in range(4):
   for row in range(8):
    for col in range(8):
     v=b[start+i*128+t*32+row*4+col//2]; v=(v>>4 if col%2==0 else v&15)
     if v:d.rectangle((x+(t%2*8+col)*2,y+14+(t//2*8+row)*2,x+(t%2*8+col)*2+1,y+14+(t//2*8+row)*2+1),fill='black')
 im.save(f'.rea_tmp/name_font_{start:x}.png')

