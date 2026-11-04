"""Board-side partial scheduler check; does not measure analog spectral peaks.

Requires an explicitly loaded diagnostic release. This historical firmware has
no build-ID query: bind the record to the programmer log separately. The limited
monitor audio is enabled by this profile during play; stop is always attempted.
"""
import argparse, datetime, hashlib, json, sys, time
from pathlib import Path
import serial
band=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(band/'host'))
from protocol import Event, Decoder, status
ap=argparse.ArgumentParser()
ap.add_argument('--port',default='COM12')
ap.add_argument('--release',type=Path,required=True)
ap.add_argument('--program-log',type=Path,required=True)
ap.add_argument('--seconds',type=float,default=60)
a=ap.parse_args()
if a.seconds<=0:ap.error('seconds must be positive')
m=json.loads((a.release/'manifest.json').read_text())
loaded=json.loads((a.program_log/'loaded_manifest.json').read_text())
fs=next(a.release.glob('*.fs'))
digest=hashlib.sha256(fs.read_bytes()).hexdigest()
if digest!=m['bitstream_sha256'] or digest!=loaded['bitstream_sha256']:
    raise RuntimeError('Programmer evidence and release hash mismatch')
count=m['partials']; decoder=Decoder();raw=bytearray();records=[]
result=dict(status='running',started=datetime.datetime.now().isoformat(),partials=count,
    bitstream_sha256=digest,program_log=str(a.program_log.resolve()),
    identity_limit='No embedded build ID; programming log plus diagnostic profile/capacity only',
    scope='Scheduler counters and independent address control, not measured analog sound or spectrum',
    records=records)
target=band/'evidence'/('hardware_diagnostic_'+str(count)+'.json')
def save():
    result['bad_crc']=decoder.bad_crc
    target.write_text(json.dumps(result,indent=2))
    target.with_suffix('.raw').write_bytes(raw)
save()
with serial.Serial(a.port,1000000,timeout=.01,write_timeout=.2) as port:
    def send(e):
        b=e.encode_uart()
        if port.write(b)!=len(b):raise IOError('Short UART write')
        time.sleep(.005)
    def poll(predicate=lambda s:True,timeout=3):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            send(Event(6));b=port.read(4096);raw.extend(b)
            for f in decoder.feed(b):
                if f[1] not in (144,145):continue
                s=status(f);s['observed_at']=time.monotonic();records.append(s)
                if predicate(s):return s
        raise RuntimeError('Diagnostic telemetry timeout: '+repr(records[-1:]))
    verified=False
    try:
        poll();verified=True
        send(Event(127));poll(lambda s:not s['playing'])
        send(Event(5));poll(lambda s:s['playing'] and s['voices']==count)
        started=time.monotonic();first=poll();max_cycles=0;next_report=0
        while time.monotonic()-started<a.seconds:
            s=poll();max_cycles=max(max_cycles,s['cycles'])
            if s['voices']!=count or s['deadline_miss'] or s['rejected']:
                raise RuntimeError('Full-load counter failure: '+repr(s))
            if time.monotonic()>=next_report:
                print('Full load',count,'elapsed',round(time.monotonic()-started),'cycles',max_cycles,flush=True)
                save();next_report=time.monotonic()+15
            time.sleep(.03)
        elapsed=s['observed_at']-first['observed_at']
        measured_rate=(s['song_sample']-first['song_sample'])/elapsed
        if not 47000<measured_rate<49000:raise RuntimeError('Sample progress inconsistent with 48 kHz')
        # Last address exercises the final lane, including the non-power-of-two
        # 37-lane profile. Preserve its frequency, silence only its envelope.
        address=count-1;step=1 if count>16384 else 3 if count>8192 else 5
        increment=(50+step*address)*32768
        send(Event(9,epoch=address,serial=increment,parameter=0,flags=64))
        poll(lambda s:s['voices']==count-1)
        send(Event(9,epoch=address,serial=increment,parameter=(50000<<16),flags=64))
        poll(lambda s:s['voices']==count)
        send(Event(5,flags=1));poll(lambda s:not s['playing'])
        if decoder.bad_crc:raise RuntimeError('Telemetry CRC failures')
        result.update(status='passed',duration_seconds=a.seconds,max_cycles=max_cycles,
            observed_sample_rate_hz=measured_rate,
            checks=['sustained active count','zero deadline misses','sample progress',
                    'last-address independent mute and re-enable','stop'])
    except Exception as e:
        result.update(status='failed',error=repr(e));raise
    finally:
        if verified:
            try:send(Event(127))
            except Exception as e:result['cleanup_error']=repr(e)
        result['finished']=datetime.datetime.now().isoformat();save()
print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
