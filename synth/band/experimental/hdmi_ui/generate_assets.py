"""Generate synthesizable Chinese glyph/tile ROMs for the 640x480 dashboard."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
out=Path(__file__).resolve().parent
lines={1:(1,'星群 / STARCLUSTER'),3:(1,'演奏台                          板载音频'),
5:(1,'实体垫音色：        八度：+0 固定'),7:(1,'最近音高：     力度：     发声数：'),
9:(1,'音高触发区 / 60—75'),10:(23,'系统状态'),12:(23,'垫桥：'),14:(23,'播放：'),16:(23,'音量：'),18:(23,'速度：'),20:(23,'面板：尚未接入'),
23:(1,'旋转  音量 速度 表情 声部 起音 释放'),
25:(1,'按压  总停 录制 复位 页面 上曲 下曲'),
27:(1,'独立键  播放  停止  八度－  八度＋'),
29:(1,'按压/八度功能待接入 · 触发高亮非持续音')}
parts=['底鼓','军鼓','踩镲','贝斯','电钢琴','簧管','主奏','合唱','拨弦','笛','钟','木琴','弓弦','管风琴','铜管','电子歌手']
extras='在线离线播放停止'+''.join(parts)
chars=set(extras+''.join(t for _,t in lines.values()))
ids={chr(i):i for i in range(128)}
for c in sorted(chars):
 if c not in ids:ids[c]=len(ids)
assert len(ids)<=256,len(ids)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
rom=[0]*4096
for c,idx in ids.items():
 if ord(c)<32:continue
 im=Image.new('L',(16,16));d=ImageDraw.Draw(im);box=d.textbbox((0,0),c,font=font);w=box[2]-box[0];h=box[3]-box[1]
 d.text(((16-w)//2-box[0],(16-h)//2-box[1]),c,font=font,fill=255)
 for y in range(16):rom[idx*16+y]=sum((1<<(15-x)) for x in range(16) if im.getpixel((x,y))>=100)
tiles=[32]*2048
for row,(col,text) in lines.items():
 assert col+len(text)<=40,(row,text)
 for i,c in enumerate(text):tiles[row*40+col+i]=ids[c]
for k in range(16):
 r=11+(k//4)*3;c=2+(k%4)*5
 for i,ch in enumerate(str(60+k)):tiles[r*40+c+i]=ids[ch]
(out/'ui_font.mem').write_text('\n'.join(f'{v:04x}' for v in rom)+'\n')
(out/'ui_tiles.mem').write_text('\n'.join(f'{v:02x}' for v in tiles)+'\n')
names=[]
for p in parts:names.extend([ids[c] for c in p.ljust(4)])
(out/'ui_names.mem').write_text('\n'.join(f'{v:02x}' for v in names)+'\n')
(out/'ui_glyphs.vh').write_text('\n'.join(f"localparam [7:0] GLYPH_{n}=8'd{ids[c]};" for n,c in [('ON','在'),('OFF','离'),('LINE','线'),('PLAY','播'),('PLAY2','放'),('STOP','停'),('STOP2','止')])+'\n')
(out/'assets.json').write_text(json.dumps({'glyphs':len(ids),'resolution':[640,480],'layout':lines},ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(ids)} glyphs, ROM assets generated')
