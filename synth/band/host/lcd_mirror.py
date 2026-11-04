"""Mirror LCD frame snapshots acknowledged by the board; read-only COM12 requests."""
import argparse
import json
import queue
import re
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
import serial
try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
    from PIL import Image, ImageDraw, ImageTk
from protocol import Event, Decoder, status

def bits(number, low, width=1):
    return (number >> low) & ((1 << width)-1)

class Screen:
    def __init__(self, build):
        def rom(name):
            return [int(x,16) for x in (build/name).read_text().split()]
        titles=build/'rtl/song_titles.vh'
        self.titles=[bytes.fromhex(x) for x in re.findall(r"^\d+:song_title=64'h([a-f0-9]{16})",titles.read_text(),re.M)] if titles.exists() else []
        self.tiles=rom('ui_tiles.mem')
        self.names=rom('ui_names.mem')
        font=rom('ui_font.mem')
        self.font=[Image.frombytes('1',(16,16),b''.join(x.to_bytes(2,'big') for x in font[i:i+16])) for i in range(0,len(font),16)]
        rtl=(build/'rtl/instrument_ui.v').read_text()
        self.labels=[bytes.fromhex(x) for x in re.findall(r"panel_label=320'h([0-9a-fA-F]{80})",rtl)]
        assert len(self.labels)==7
        self.glyph={name:int(n) for name,n in re.findall(r"GLYPH_(\w+)=8'd(\d+)",(build/'rtl/ui_glyphs.vh').read_text())}
    def render(self,s):
        im=Image.new('RGB',(640,480),'#0b1424')
        d=ImageDraw.Draw(im)
        for box,color in [((0,0,639,63),'#13283c'),((0,64,639,143),'#17283b'),((360,160,639,351),'#142438'),((0,360,639,479),'#101f31')]:
            d.rectangle(box,fill=color)
        tiles=self.tiles[:1200]
        fg=['#d9e5f2']*1200
        for row in range(30):
            color='#58dcc5' if row in (1,23,25,27) else '#f2b768' if row==29 else '#94acc3' if row>=23 else '#d9e5f2'
            fg[row*40:(row+1)*40]=[color]*40
        for k in range(16):
            x=16*(1+5*(k%4));y=16*(10+3*(3-k//4 if self.titles else k//4));hit=bits(s,50+k)
            cue=bool(self.titles and bits(s,109,2)==3 and bits(s,97) and bits(s,93,4)==k)
            d.rectangle((x,y,x+63,y+31),fill='#f4c451' if cue else '#3dcdb3' if hit else '#20354b',outline='#3d586e')
            for row in range(y//16,y//16+2):
                for col in range(x//16,x//16+4):fg[row*40+col]='#201a11' if cue else '#081b22' if hit else '#d9e5f2'
        def put(row,col,seq):
            start=row*40+col;tiles[start:start+len(seq)]=seq
        def num(row,col,val,width=1):put(row,col,str(val).zfill(width)[-width:].encode())
        page=bits(s,107,2);mode=bits(s,109,2)
        put(23,0,self.labels[0]);put(25,0,self.labels[1+page]);put(27,0,self.labels[6 if mode==3 else 5])
        num(23,6,bits(s,99,4),2);octave=bits(s,103,4);octave-=16 if octave>=8 else 0
        put(23,14,b'-' if octave<0 else b'+');num(23,15,abs(octave))
        for col,bit in [(22,112),(29,111)]:num(23,col,bits(s,bit))
        num(23,38,page)
        song=bits(s,124,2)+(bits(s,98)*4 if self.titles else 0)
        if self.titles and song<len(self.titles):put(3,9,self.titles[song])
        if self.titles and mode==3 and bits(s,97):num(27,30,bits(s,93,4)+1,2)
        if mode!=3:
            for col,bit in [(5,86),(16,87),(25,88),(34,89)]:num(27,col,bits(s,bit))
        if page==0:
            num(25,6,bits(s,117,7),3);num(25,18,bits(s,67,14),5);num(25,34,bits(s,81,4),2)
        elif page==1:
            for i in range(4):num(25,15+i*2,bits(s,113+i))
        elif page==2:num(25,10,mode);num(25,20,bits(s,85))
        else:num(25,6,1+song);num(25,18,bits(s,126));num(25,28,bits(s,127))
        j=bits(s,46,4)*4;put(5,7,self.names[j:j+4]);fg[207:211]=['#58dcc5']*4
        num(7,7,bits(s,32,7),3);num(7,15,bits(s,39,7),3);num(7,25,bits(s,16,16),3)
        put(12,27,[self.glyph['ON' if bits(s,66) else 'OFF'],self.glyph['LINE']]);fg[12*40+27]='#58dcc5' if bits(s,66) else '#f2b768'
        put(14,27,[self.glyph['PLAY' if bits(s,0) else 'STOP'],self.glyph['PLAY2' if bits(s,0) else 'STOP2']])
        num(16,27,bits(s,1,7),3);num(18,27,bits(s,8,8),3)
        for i,g in enumerate(tiles):
            if g!=32:
                x=(i%40)*16;y=(i//40)*16
                im.paste(fg[i],(x,y,x+16,y+16),self.font[g])
        return im
def main():
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--port',default='COM12');p.add_argument('--log-dir',type=Path,required=True);a=p.parse_args()
    a.log_dir.mkdir(parents=True,exist_ok=True)
    if (a.build/"score_map.mem").exists():
        from score_mirror import run
        return run(a)
    screen=Screen(a.build);expected=json.loads((a.build/'manifest.json').read_text())['build_id']
    events=queue.Queue(maxsize=2);quit_event=threading.Event();pause=a.log_dir/'release_port'
    def publish(item):
        if events.full():
            try:events.get_nowait()
            except queue.Empty:pass
        events.put_nowait(item)
    def poll():
        with (a.log_dir/'frames.jsonl').open('a',encoding='utf8',buffering=1) as log:
            while not quit_event.is_set():
                try:
                    if pause.exists():
                        publish(('message','等待烧录程序释放串口'));quit_event.wait(.3);continue
                    with serial.Serial(a.port,1000000,timeout=.025) as link:
                        decoder=Decoder();build=None;req=0;panel_info='等待读取面板';seen=time.monotonic();last_rx=seen
                        while not (quit_event.is_set() or pause.exists()):
                            identity=req%20==0 or build is None
                            config=req%10==5
                            link.write(Event(18 if identity else 20,source=1,flags=0 if identity or config else 77).encode_uart());req+=1
                            packet=link.read(4096)
                            before=bytes(decoder.buffer);errors=decoder.bad_crc
                            replies=decoder.feed(packet)
                            if decoder.bad_crc!=errors:
                                (a.log_dir/'last_bad_rx.bin').write_bytes(before+packet)
                            for raw in replies:
                                last_rx=time.monotonic()
                                if raw[1]==161:
                                    build=int.from_bytes(raw[4:8],'little')
                                    identity=dict(t=time.time(),build_id=build,features=int.from_bytes(raw[20:24],'little'),bad_crc=decoder.bad_crc)
                                    (a.log_dir/'identity.json').write_text(json.dumps(identity),encoding='utf8')
                                if raw[1]==163:
                                    panel_info=f'声部 {raw[2]}　模式 {raw[5]}　延音 {raw[4]&1}'
                                    log.write(json.dumps(dict(t=time.time(),mode=raw[5],part=raw[2],record=raw[6],replay=raw[7],halt=raw[8]))+'\n')
                                if build==expected and raw[1]==164:
                                    frame=int.from_bytes(raw[2:4],'little');s=int.from_bytes(raw[4:20],'little');adc=int.from_bytes(raw[20:26],'little')
                                    mv=[bits(adc,12*i,12) for i in range(4)];seen=time.monotonic()
                                    obj=dict(t=time.time(),frame=frame,state=f'{s:032x}',mv=mv,crc_errors=decoder.bad_crc)
                                    log.write(json.dumps(obj)+'\n');publish(('frame',obj))
                            if time.monotonic()-last_rx>4:
                                publish(('message','未收到板上回读，正在重新打开 '+a.port));break
                            if time.monotonic()-last_rx>1.5:publish(('message','板上回读中断，等待重新连接'))
                            elif build is not None and build!=expected:
                                publish(('message',f'板上实测　{panel_info}　·　完整画面等待回读固件'))
                            elif time.monotonic()-seen>1.5:publish(('message','未收到有效屏幕帧，画面已暂停'))
                            quit_event.wait(.065)
                except (serial.SerialException,OSError) as ex:
                    publish(('message','串口未连接 · 等待 '+a.port));quit_event.wait(.6)
    w=tk.Tk();w.title('星群 · FPGA 实时屏幕');w.configure(bg='#101f31')
    display=tk.Label(w,bg='#0b1424',fg='white',text='等待 FPGA 屏幕帧',font=('Microsoft YaHei UI',16));display.pack(fill='both',expand=True)
    bar=tk.StringVar(value='连接 '+a.port);tk.Label(w,textvariable=bar,bg='#101f31',fg='#70dfce',font=('Microsoft YaHei UI',11)).pack(pady=6)
    knobs=tk.StringVar(value='等待旋钮参数')
    tk.Label(w,textvariable=knobs,bg='#101f31',fg='white',font=('Microsoft YaHei UI',11)).pack()
    checks=tk.Frame(w,bg='#101f31');checks.pack()
    prompt=tk.StringVar(value='收到实时帧后可进行联测')
    tk.Label(w,textvariable=prompt,bg='#101f31',fg='white',font=('Microsoft YaHei UI',10)).pack(pady=2)
    run={};latest_frame=[0.]
    def begin(kind):
        if time.monotonic()-latest_frame[0]>1.5:
            prompt.set('等待液晶帧回读，暂不能开始联测');return
        run.clear();run.update(kind=kind,start=time.monotonic(),frames=0,lo=[4096]*4,hi=[0]*4,picked=0,notes=set(),mode=False)
        prompt.set('请依次将四个推子从低端推到高端再推回（40 秒）' if kind=='faders' else '切换至模式三，跟随实体灯敲击。结束后点击“记录灯声结果”。')
    def save(result):
        with (a.log_dir/'physical_checks.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(t=time.time(),**result),ensure_ascii=False)+'\n')
    def observe(v,s):
        latest_frame[0]=time.monotonic()
        if not run:return
        run['frames']+=1
        if run['kind']=='faders':
            if bits(s,111):
                for i,m in enumerate(v['mv']):run['lo'][i]=min(run['lo'][i],m);run['hi'][i]=max(run['hi'][i],m)
                run['picked']|=bits(s,113,4)
            elapsed=time.monotonic()-run['start']
            prompt.set(f'请移动 {min(4,1+int(elapsed//10))} 号推子：从低到高再推回　剩余 {max(0,40-int(elapsed))} 秒')
            if elapsed>=40:
                passed=[run['lo'][i]<250 and run['hi'][i]>=2875 and bool(run['picked']&(1<<i)) for i in range(4)]
                save(dict(kind='faders',frames=run['frames'],min_mV=run['lo'],max_mV=run['hi'],pickup_mask=run['picked'],passed=passed))
                prompt.set('四路全行程及接管：'+' ／ '.join('通过' if x else '未测全' for x in passed));run.clear()
        elif bits(s,109,2)==3:
            run['mode']=True
            if bits(s,66) and bits(s,50,16):
                run['notes'].add(bits(s,32,7))
            prompt.set(f"学习模式已读回　已观察到 {len(run['notes'])} 种音高。请核对实体灯和声音。")
    def listening():
        if run.get('kind')!='lesson' or not run.get('mode'):
            prompt.set('请先开始跟灯测试并切到模式三');return
        from tkinter import messagebox
        good=messagebox.askyesnocancel('实体垫验收','是否看见目标垫亮起，敲对后发声并切换到下一提示？',parent=w)
        if good is None:return
        save(dict(kind='lesson',frames=run['frames'],mode_seen=run['mode'],observed_notes=sorted(run['notes']),lights_and_audio_user_confirmed=good))
        run.clear();prompt.set('已记录现场反馈')
    for label,cmd in [('测试四个推子',lambda:begin('faders')),('测试跟灯',lambda:begin('lesson')),('记录灯声结果',listening)]:
        tk.Button(checks,text=label,command=cmd).pack(side='left',padx=4)
    w.geometry('820x610');t=threading.Thread(target=poll,daemon=True);t.start()
    def update():
        try:
            kind,v=events.get_nowait()
            if kind=='message':bar.set(v)
            else:
                s=int(v['state'],16);observe(v,s);panel=Image.new('RGB',(800,480),'#0b1424');panel.paste(screen.render(s),(80,0))
                photo=ImageTk.PhotoImage(panel);display.configure(image=photo,text='');display.image=photo
                volts='   '.join(f'{i+1}号 {n/1000:.2f}V' for i,n in enumerate(v['mv']))
                knobs.set('    '.join(f'{label} {bits(s,low,width)}' for label,low,width in
                    [('总音量',1,7),('速度',8,8),('表情',117,7),('声部',99,4),('起音',67,14),('释音',81,4)]))
                (a.log_dir/'displayed.json').write_text(json.dumps(v),encoding='utf8')
                bar.set(f"实时帧 {v['frame']}   {volts}   接管 {''.join(str(bits(s,113+i)) for i in range(4))}")
        except queue.Empty:pass
        w.after(65,update)
    def close():quit_event.set();w.destroy()
    w.protocol('WM_DELETE_WINDOW',close);update();w.mainloop()
if __name__=='__main__':main()
