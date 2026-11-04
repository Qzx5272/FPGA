"""Reconstruct the 800x480 FPGA scanout from its tile ROM and six CRC-framed visual packets."""
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
import json
import re

from PIL import Image,ImageDraw,ImageTk
import serial
from protocol import Decoder,Event

COLORS=['#FAF5E9','#E9DFCF','#D5C7B3','#84796B','#292722','#D49B86','#A33727','#FAC751']
def field(word,bit,width):
    return (word>>bit)&((1<<width)-1)

class Artwork:
    def __init__(self,build):
        def rom(name):
            return [int(x,16) for x in (build/name).read_text().split()]
        blocks=rom('score_map.mem')
        ids=rom('score_tiles.mem')
        self.index=[i for k in blocks for i in ids[k*8:k*8+8]]
        row_ids=rom('score_rows.mem')
        rows=rom('score_pixels.mem')
        palette=bytes.fromhex(''.join(s[1:] for s in COLORS))+bytes(768-24)
        self.tiles=[]
        for j in range(0,len(row_ids),8):
            data=bytes(field(rows[k],x*3,3) for k in row_ids[j:j+8] for x in range(8))
            tile=Image.frombytes('P',(8,8),data);tile.putpalette(palette)
            self.tiles.append(tile.convert('RGB'))
        layout=(build/'rtl/score_layout.vh').read_text()
        self.show_parameters='SHOW_PARAMETERS=1' in layout
        self.numeric_attack='ATTACK_NUMERIC=1' in layout
        self.offsets={key:int(value) for key,value in re.findall(r'(\w+)_BASE=(\d+)',layout)}
        self.pages=[self.sprite(i*6000,800,480) for i in range(4)]
    def sprite(self,start,w,h):
        result=Image.new('RGB',(w,h))
        for y in range(0,h,8):
            for x in range(0,w,8):
                result.paste(self.tiles[self.index[start]],(x,y));start+=1
        return result
    def render(self,s,v):
        page=field(s,107,2);im=self.pages[page].copy();d=ImageDraw.Draw(im)
        def graphic(key,index,w,h,x,y):
            im.paste(self.sprite(self.offsets[key]+index*w*h//64,w,h),(x,y))
        def number(n,width,x,y):
            for i,c in enumerate(str(n).zfill(width)[-width:]):graphic('DIGIT',int(c),16,32,x+i*16,y)
        left=[field(v,436+6*i,6) for i in range(64)]
        right=[field(v,52+6*i,6) for i in range(64)]
        if self.show_parameters:
            number(field(s,1,7),3,264,8)
        if page==0:
            if self.show_parameters:
                number(field(s,117,7),3,144,80)
                number(field(s,81,4),2,608,112)
                if self.numeric_attack:
                    number(field(s,67,14),5,608,72)
                else:
                    length=field(s,74,7)
                    if length:d.rectangle((608,88,607+length,90),fill=COLORS[6])
            graphic('PART',field(s,46,4),240,64,280,72)
            number(field(s,46,4),2,432,136)
            graphic('NOTE',field(s,32,7),64,32,136,176)
            for start,bits,x in [(39,7,392),(8,8,656)]:number(field(s,start,bits),3,x,176)
            for dx in range(504):
                i,f=divmod(dx,8);y=262-((left[i]-32)*8+(left[i+1]-left[i])*f>>3)
                d.line((144+dx,y,144+dx,y+1),fill=COLORS[6])
            for j in range(4):
                x=114+j%2*375;y=332+j//2*60
                d.rectangle((x,y-1,x+2*field(v,12+j*7,7),y+1),fill=COLORS[6])
        elif page==1:
            levels=[field(v,820+i*4,4) for i in range(32)]
            for dx in range(496):
                i,f=divmod(dx,16);y=372-((levels[i]*16+(levels[i+1]-levels[i])*f)*10>>4)
                d.line((144+dx,max(y-1,200),144+dx,min(y+1,375)),fill=COLORS[6])
        elif page==2:
            x,y=left[0],right[0]
            for u,w in zip(left,right):
                while True:
                    xx,yy=88+x*4,169+(63-y)*4
                    d.rectangle((xx,yy,xx+3,yy+3),fill=COLORS[6])
                    if (x,y)==(u,w):break
                    x+=(u>x)-(u<x);y+=(w>y)-(w<y)
            for x,bit in [(469,46),(629,40)]:
                h=field(v,bit,6)*2
                if h:d.rectangle((x,398-h,x+32,397),fill=COLORS[6])
        else:
            song=field(s,98,1)*4+field(s,124,2)
            graphic('SONG',song,352,64,224,64)
            mode=3 if field(s,109,2)==3 else 2 if field(v,11,1) else field(v,10,1)
            graphic('MODE',mode,160,32,424,256)
            look=field(v,948,32)
            if look>>31:
                number(field(look,27,4)+1,2,432,216);graphic('NOTE',field(look,20,7),64,32,488,216)
                if field(look,19,1):number(field(look,15,4)+1,2,520,368)
                x=460+field(look,8,7)*2;d.rectangle((x,414,x+4,426),fill=COLORS[6])
            if field(s,97,1):
                p=field(s,93,4)
                x,y=50+(p%4)*76,172+(3-p//4)*62;d.rectangle((x,y,x+65,y+53),outline=COLORS[7],width=3)
            if field(v,0,3):number(field(v,0,3),1,688,256)
            length=2*field(v,3,7)
            if length:d.rectangle((430,347,429+length,349),fill=COLORS[6])
        return im

def run(args):
    art=Artwork(args.build);args.log_dir.mkdir(exist_ok=True,parents=True)
    messages=queue.Queue(2);quit_event=threading.Event()
    def publish(item):
        if messages.full():messages.get_nowait()
        messages.put_nowait(item)
    def poll():
        while not quit_event.is_set():
            if (args.log_dir/'release_port').exists():quit_event.wait(.3);continue
            try:
                with serial.Serial(args.port,1000000,timeout=.006) as port:
                    decoder=Decoder()
                    def query(flags,reply,index=None):
                        port.write(Event(20,source=1,flags=flags).encode_uart())
                        until=time.monotonic()+.15
                        while time.monotonic()<until:
                            for raw in decoder.feed(port.read(1024)):
                                if raw[1]==reply and (index is None or raw[3]==index):return raw
                        raise TimeoutError('等待 FPGA 帧')
                    while not quit_event.is_set() and not (args.log_dir/'release_port').exists():
                        raw=query(77,164);frame=int.from_bytes(raw[2:4],'little')
                        s=int.from_bytes(raw[4:20],'little');v=0
                        for i in range(7):
                            chunk=query(96+i,165,i)
                            if int.from_bytes(chunk[4:6],'little')!=frame:break
                            v|=int.from_bytes(chunk[6:26],'little')<<(i*160)
                        else:
                            publish((art.render(s,v),frame,decoder.bad_crc))
            except (OSError,serial.SerialException,TimeoutError) as e:
                publish(str(e));quit_event.wait(.3)
    root=tk.Tk();root.title('星群 · FPGA 实时屏幕')
    panel=tk.Label(root);panel.pack();info=tk.Label(root,text='正在连接 FPGA');info.pack()
    def tick():
        try:
            item=messages.get_nowait()
            if isinstance(item,str):info.config(text=item)
            else:
                im,frame,crc=item;photo=ImageTk.PhotoImage(im);panel.configure(image=photo);panel.image=photo
                info.config(text=f'FPGA 实时帧 {frame}   CRC 错误 {crc}')
                (args.log_dir/'displayed.json').write_text(json.dumps(dict(frame=frame,crc_errors=crc,t=time.time())))
        except queue.Empty:pass
        root.after(50,tick)
    threading.Thread(target=poll,daemon=True).start()
    root.protocol('WM_DELETE_WINDOW',lambda:(quit_event.set(),root.destroy()));tick();root.mainloop()
