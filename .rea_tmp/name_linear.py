from pathlib import Path
from PIL import Image,ImageDraw
b=Path('霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes()
im=Image.new('RGB',(16*60,24*58),'white');d=ImageDraw.Draw(im)
for i in range(384):
 x=i%16*60;y=i//16*58;start=0xd9000+i*128
 d.text((x,y),f'{start:05X}',fill='black')
 for row in range(16):
  for col in range(16):
   v=b[start+row*8+col//2];v=(v>>4 if col%2==0 else v&15)
   if v:d.rectangle((x+col*2,y+14+row*2,x+col*2+1,y+14+row*2+1),fill='black')
im.save('.rea_tmp/name_linear.png')
