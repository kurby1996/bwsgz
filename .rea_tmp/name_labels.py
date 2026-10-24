exec(open('.rea_tmp/name_extract.py',encoding='utf8').read().split('for mode')[0])
texts=[]
for start,end in [(0x428cc,0x42a00),(0x42700,0x428cc)]:
 p=start
 while p<end:
  q=b.find(b'\0',p,end)
  if q<0:q=end
  text=b[p:q]
  if text and any(v>=0x81 for v in text):texts.append((p,text))
  p=q+1
im=Image.new('RGB',(900,len(texts)*56),'white');d=ImageDraw.Draw(im)
for row,(off,text) in enumerate(texts):
 x=80;y=row*56;d.text((0,y),f'{off:X}',fill='black');i=0
 while i<len(text):
  c=text[i];i+=1
  if c==255:continue
  if c==10:x+=12;continue
  if c<0x81:d.text((x,y+12),chr(c) if c>=32 else '.',fill='black');x+=10;continue
  if i>=len(text):break
  c=c*256+text[i];i+=1;data=glyph(c)
  if len(data)!=32:continue
  for t in range(4):
   for py in range(8):
    for px in range(8):
     if data[t*8+py]&(128>>px):d.rectangle((x+(t%2*8+px)*2,y+(t//2*8+py)*2,x+1+(t%2*8+px)*2,y+1+(t//2*8+py)*2),fill='black')
  x+=34
im.save('.rea_tmp/name_labels.png')

