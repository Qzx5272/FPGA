"""Small bounded SMF reader/writer. No sample playback, no silently truncated MIDI."""
import struct
from pathlib import Path
from score import validate


def vlq(value):
    if not 0<=value<=0xfffffff:raise ValueError('MIDI时间超出范围')
    out=[value&127];value>>=7
    while value:out.insert(0,128|(value&127));value>>=7
    return bytes(out)


def read_vlq(data,pos):
    value=0
    for _ in range(4):
        if pos>=len(data):raise ValueError('截断的MIDI数据')
        b=data[pos];pos+=1;value=(value<<7)|(b&127)
        if not b&128:return value,pos
    raise ValueError('非法MIDI变长整数')


def read_midi(path):
    data=Path(path).read_bytes()
    if len(data)>8*1024*1024 or len(data)<14 or data[:4]!=b'MThd':raise ValueError('不是有效MIDI文件')
    size=struct.unpack('>I',data[4:8])[0]
    if size<6 or 8+size>len(data):raise ValueError('MIDI头截断')
    fmt,tracks,division=struct.unpack('>HHH',data[8:14])
    if fmt not in (0,1) or not division or division&0x8000 or tracks>128:raise ValueError('仅支持PPQN格式0/1 MIDI')
    pos=8+size;messages=[];tempos=[];end=0
    for _ in range(tracks):
        if data[pos:pos+4]!=b'MTrk' or pos+8>len(data):raise ValueError('缺少MIDI轨道')
        length=struct.unpack('>I',data[pos+4:pos+8])[0];pos+=8
        block=data[pos:pos+length];pos+=length
        if len(block)!=length:raise ValueError('MIDI轨道截断')
        i=0;tick=0;running=None
        while i<len(block):
            delta,i=read_vlq(block,i);tick+=delta;end=max(end,tick)
            if i>=len(block):raise ValueError('缺少MIDI消息')
            status=block[i]
            if status&128:i+=1
            elif running is not None:status=running
            else:raise ValueError('非法MIDI running status')
            if status==255:
                if i>=len(block):raise ValueError('截断的meta事件')
                kind=block[i];i+=1;n,i=read_vlq(block,i);payload=block[i:i+n];i+=n
                if len(payload)!=n:raise ValueError('meta事件截断')
                if kind==81:
                    if n!=3:raise ValueError('非法速度事件')
                    tempos.append((tick,int.from_bytes(payload,'big')))
                if kind==47:break
                running=None
            elif status in (240,247):
                n,i=read_vlq(block,i);i+=n;running=None
                if i>len(block):raise ValueError('SysEx截断')
            elif 128<=status<240:
                running=status;count=1 if status&240 in (192,208) else 2
                payload=block[i:i+count];i+=count
                if len(payload)!=count or any(x&128 for x in payload):raise ValueError('非法MIDI数据字节')
                if status&240 in (128,144):messages.append((tick,status,payload))
            else:raise ValueError('MIDI文件包含不支持的系统消息')
    # Keep musical time; preserve constant initial tempo. Tempo maps need a future format.
    tempos=sorted(tempos)
    if len({v for t,v in tempos})>1:raise ValueError('此MIDI含变速图；当前格式不支持，未截断导入')
    tempo=tempos[0][1] if tempos else 500000
    bpm=round(60000000/tempo) if tempo else 0
    if not 40<=bpm<=240:raise ValueError('MIDI速度超出40–240 BPM')
    live={};events=[];serial=1
    for tick,status,payload in sorted(messages,key=lambda e:(e[0],e[1]&240==144 and bool(e[2][1]))):
        channel=status&15;note,velocity=payload
        part=(0 if note in (35,36) else 1 if note in (38,40) else 2) if channel==9 else min(channel+3,14)
        key=(channel,note);sample=round(tick*24000/division)
        if status&240==144 and velocity:
            if key in live:raise ValueError('同通道同音重叠，需先整理MIDI')
            live[key]=(serial,part,sample)
            events.append(dict(sample=sample,kind=0,part=part,note=note,velocity=velocity,serial=serial));serial+=1
        elif key in live:
            identity,role,on=live.pop(key)
            events.append(dict(sample=max(on+1,sample),kind=1,part=role,note=note,velocity=0,serial=identity))
    duration=max(round(end*24000/division)+24000,max((e['sample'] for e in events),default=0)+2)
    for (channel,note),(identity,part,on) in live.items():events.append(dict(sample=duration-1,kind=1,part=part,note=note,velocity=0,serial=identity))
    score=dict(format='starcluster-score-1',sample_rate=48000,bpm=120,duration_samples=duration,
               roles=['底鼓','军鼓','踩镲','贝斯','键盘','簧音','主奏','合唱'],
               performance=dict(tempo=bpm),events=sorted(events,key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial'])))
    return validate(score)


def write_midi(path,score):
    validate(score);tempo=round(60000000/score.get('performance',{}).get('tempo',120))
    track=bytearray(b'\0\xff\x51\x03'+tempo.to_bytes(3,'big'));last=0
    for e in score['events']:
        if e['kind'] not in (0,1):continue
        tick=round(e['sample']*480/24000)
        channel=9 if e['part']<3 else (e['part']-3)%16
        if channel==9:channel=15
        # Drum channels retain their semantic kick/snare/hat identity.
        note=(36,38,42)[e['part']] if e['part']<3 else e['note']
        track.extend(vlq(tick-last)+bytes([(144 if e['kind']==0 else 128)|channel,note,e['velocity'] if e['kind']==0 else 0]));last=tick
    track.extend(b'\0\xff\x2f\0')
    Path(path).write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,480)+b'MTrk'+struct.pack('>I',len(track))+track)
