"""Load audited song candidate to SRAM, or play 96s with UART telemetry."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess,sys,time
import serial
root=Path(__file__).resolve().parents[3];b=Path('D:/StarclusterBuilds/pcm5102_song_audio_20261031')
sys.path.insert(0,str(root/'synth/band/host'))
from protocol import Event,Decoder,status,singer_status
ap=argparse.ArgumentParser();ap.add_argument('--program',action='store_true');ap.add_argument('--play',action='store_true');ap.add_argument('--port',default='COM12');a=ap.parse_args()
assert a.program!=a.play,'Choose exactly one operation'
m=json.loads((b/'audit.json').read_text());assert m['status']=='audited_pending_board_test'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in m['sources'].items():assert sha(b/n)==h,n
bit=b/'impl/pnr/pcm5102_song.fs';assert sha(bit)==m['bitstream_sha256']
out=root/'synth/band/evidence'/('pcm5102_song_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
if a.program:
    cli='D:/Gowin/Gowin_V1.9.12.03_x64/Programmer/bin/programmer_cli.exe'
    base=['--device','GW5AST-138B','--cable-index','4','--location','0','--channel','0']
    for name,cmd in [('probe',base+['--run','0']),('sram',base+['--run','2','--fsFile',str(bit)])]:
        p=subprocess.run([cli,*cmd],capture_output=True,text=True,errors='replace',timeout=90)
        log=p.stdout+p.stderr;(out/(name+'.log')).write_text(log)
        assert p.returncode==0 and not re.search(r'\b(error|failed|failure)\b',log,re.I),log
        assert 'Finished.' in log and ('100%' in log if name=='sram' else '0x0001081B' in log),log
    (out/'loaded_manifest.json').write_text(json.dumps(m,indent=2))
    (b/'last_program.json').write_text(json.dumps(dict(evidence=str(out),sha256=sha(bit))))
    print('SRAM loaded; Flash unchanged; playback not yet started. '+str(out));raise SystemExit
loaded=json.loads((b/'last_program.json').read_text());assert loaded['sha256']==sha(bit)
d=Decoder();raw=bytearray();verified=False;records=[]
r=dict(status='running',bitstream_sha256=sha(bit),program_evidence=loaded['evidence'],records=records,
 scope='96s default score through FPGA PCM5102 I2S; digital telemetry, user listening required',master=32)
port=serial.Serial(a.port,1000000,timeout=.02,write_timeout=.2)
def send(e):
    data=e.encode_uart();assert port.write(data)==len(data);time.sleep(.05)
def poll(kind=6):
    target={6:(128,129),18:(161,),19:(162,)}[kind]
    end=time.monotonic()+3
    while time.monotonic()<end:
        send(Event(kind,part=15 if kind==19 else 0));time.sleep(.02)
        data=port.read(4096);raw.extend(data)
        for f in d.feed(data):
            if f[1] in target:return f
    raise RuntimeError('UART timeout for '+str(kind))
def save():
    r['bad_crc']=d.bad_crc;(out/'result.json').write_text(json.dumps(r,indent=2));(out/'uart.raw').write_bytes(raw)
try:
    f=poll(18);identity=int.from_bytes(f[4:8],'little');assert identity==m['build_id'],hex(identity)
    verified=True;r['identity']=identity
    for e in (Event(5,flags=1),Event(127),Event(10,parameter=32),Event(15,parameter=120)):
        send(e);time.sleep(.05)
        data=port.read(4096);raw.extend(data);d.feed(data)
    send(Event(5,flags=0))
    data=port.read(4096);raw.extend(data);d.feed(data)
    start=time.monotonic();last_print=-30;peak=0;previous=0;seen_play=False
    while time.monotonic()-start<105:
        s=status(poll());h=singer_status(poll(19));elapsed=time.monotonic()-start
        peak=max(peak,s['voices']);seen_play|=s['playing'];assert s['song_sample']>=previous
        previous=s['song_sample'];records.append(dict(elapsed=elapsed,**s,health=h));save()
        assert not any(s[k] for k in ('rejected','deadline_miss','clips')),s
        assert not any(h[k] for k in ('dropped','dac_dropped','dac_underruns')),h
        assert d.bad_crc==0,'UART CRC error'
        if elapsed-last_print>=20:print('Playback %.1fs: sample=%d voices=%d, counters clean'%(elapsed,previous,s['voices']),flush=True);last_print=elapsed
        if seen_play and not s['playing']:
            assert previous==4608000 and peak>0,(previous,peak)
            r.update(status='passed_digital_song',peak_voices=peak,final_sample=previous);break
        time.sleep(.1)
    else:raise RuntimeError('Song did not finish')
except Exception as e:
    r.update(status='failed',error=repr(e));raise
finally:
    if verified:
        for e in (Event(5,flags=1),Event(127),Event(10,parameter=0)):send(e)
        try:r['final_state']=status(poll())
        except Exception as e:r['cleanup_error']=repr(e)
    port.close();r['finished']=datetime.datetime.now().isoformat();save()
print(json.dumps({k:v for k,v in r.items() if k!='records'},indent=2))
