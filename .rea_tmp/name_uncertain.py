exec(open('.rea_tmp/name_extract.py',encoding='utf8').read().split('for mode')[0])
ids=[13,42,44,64,82,113,117,138,154,164,167,180,184,195,217,220,234,240,245,249,250,264,278,284,287,298,303,305,307,310,311,312,317,318,319,331,332,337,349]
im=Image.new('RGB',(5*240,8*90),'white');d=ImageDraw.Draw(im)
for n,i in enumerate(ids):
 x=n%5*240;y=n//5*90;d.text((x,y),str(i),fill='black')
 raw=b[0x4c8d4+i*16:0x4c8d4+i*16+6]
 for ch in range(3):
  c=int.from_bytes(raw[ch*2:ch*2+2],'big')
  if c==0:break
  data=glyph(c)
  for t in range(4):
   for row in range(8):
    for col in range(8):
     if data[t*8+row]&(128>>col):d.rectangle((x+30+ch*66+(t%2*8+col)*4,y+(t//2*8+row)*4,x+33+ch*66+(t%2*8+col)*4,y+3+(t//2*8+row)*4),fill='black')
im.save('.rea_tmp/name_uncertain.png')
