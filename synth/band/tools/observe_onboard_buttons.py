"""Operator-assisted transport observation. Sends identity/status queries only.

Start with stopped/zero voices. After READY, operator presses S0,S1,S0,S2,
leaving at least two seconds between presses. No other controller should send
transport commands. Observed transitions do not independently identify GPIOs,
prove electrical debounce, or constitute an audible-output test.
"""
import argparse,datetime,hashlib,json,sys,time
from pathlib import Path
import serial

band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from protocol import Event,Decoder,status
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--release',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--port',default='COM12')
ap.add_argument('--step-timeout',type=float,default=60)
a=ap.parse_args()
if a.step_timeout<=0:ap.error('step-timeout must be positive')
if a.output.exists() or a.output.with_suffix('.raw').exists():raise RuntimeError('Preserve prior evidence')
m=json.loads((a.release/'manifest.json').read_text(encoding='utf-8'))
assert m.get('onboard_controls') and m.get('build_id')
assert hashlib.sha256((a.release/'starcluster_band.fs').read_bytes()).hexdigest()==m['bitstream_sha256']
a.output.parent.mkdir(parents=True,exist_ok=True)
decoder=Decoder();raw=bytearray();observations=[]
record=dict(status='running',started=datetime.datetime.now().isoformat(),build_id=m['build_id'],
 bitstream_sha256=m['bitstream_sha256'],commands_sent=[18,6],observations=observations,
 driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 scope='Operator-assisted S0/S1/S0/S2 sequence inferred from transport telemetry; no raw GPIO readback or independent source discrimination, analog/debounce/cold-start proof')
def save():
 record['crc_errors']=decoder.bad_crc
 a.output.write_text(json.dumps(record,indent=2),encoding='utf-8')
 a.output.with_suffix('.raw').write_bytes(raw)
try:
 with serial.Serial(a.port,1000000,timeout=.02,write_timeout=.2) as port:
  def poll(kind):
   packet=Event(kind).encode_uart()
   if port.write(packet)!=len(packet):raise IOError('Short query write')
   time.sleep(.03);block=port.read(8192);raw.extend(block)
   frames=decoder.feed(block)
   if decoder.bad_crc:raise RuntimeError('Telemetry CRC error')
   return frames
  matched=False;until=time.monotonic()+4
  while not matched and time.monotonic()<until:
   for frame in poll(18):
    if frame[1]==161:
     if int.from_bytes(frame[4:8],'little')!=m['build_id']:raise RuntimeError('Unexpected board identity')
     matched=True
  if not matched:raise RuntimeError('No board identity')
  steps=[('initial stopped',False),('S0 play',True),('S1 stop',False),('S0 replay',True),('S2 panic',False)]
  for index,(label,playing) in enumerate(steps):
   until=time.monotonic()+(4 if index==0 else a.step_timeout);observed=False
   if index:print('READY: '+label,flush=True)
   while time.monotonic()<until and not observed:
    for frame in poll(6):
     if frame[1] not in (128,129):continue
     value=status(frame)
     if value['playing']==playing and (playing or value['voices']==0):
      observations.append(dict(step=label,time=datetime.datetime.now().isoformat(),telemetry=value))
      observed=True;save();break
   if not observed:raise RuntimeError('No expected transition: '+label)
  record['status']='passed_observed_transport_sequence'
except Exception as error:
 record.update(status='incomplete_or_failed',error=str(error));raise
finally:
 record['finished']=datetime.datetime.now().isoformat();save()
 a.output.with_suffix('.driver.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(record,indent=2))
