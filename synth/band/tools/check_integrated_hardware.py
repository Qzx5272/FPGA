"""Bounded low-volume song audition and real UART diagnostics; always stops."""
from pathlib import Path
import argparse,json,time,sys
import serial
p=argparse.ArgumentParser();p.add_argument('--build',required=True);p.add_argument('--port',default='COM12');p.add_argument('--seconds',type=float,default=10);a=p.parse_args()
b=Path(a.build);identity=json.loads((b/'pc_identity.json').read_text());audit=json.loads((b/'audit.json').read_text())
assert identity['build_id']==audit['build_id']
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from protocol import Event,Decoder,status,singer_status
decoder=Decoder();states=[];singers=[];configs=[];ids=[]
def collect(port):
 for raw in decoder.feed(port.read(4096)):
  if raw[1] in (128,129):states.append(status(raw))
  elif raw[1]==162:singers.append(singer_status(raw))
  elif raw[1]==163:configs.append({'part':raw[2],'octave':int.from_bytes(raw[3:4],'little',signed=True),'sustain':bool(raw[4]&1),'mic_mode':raw[5],'record_counter':raw[6],'replay_counter':raw[7],'halt_counter':raw[8]})
  elif raw[1]==161:ids.append({'build_id':int.from_bytes(raw[4:8],'little'),'features':int.from_bytes(raw[20:24],'little')})
with serial.Serial(a.port,1000000,timeout=.02) as port:
 settle=time.monotonic()+.3
 while time.monotonic()<settle:port.read(4096)
 port.reset_input_buffer()
 def send(event):port.write(event.encode_uart());time.sleep(.01);collect(port)
 send(Event(18,source=1));send(Event(10,source=1,parameter=20));send(Event(5,source=1,flags=0))
 print('Audition: master=20, song playing; monitoring real counters...',flush=True)
 start=time.monotonic();i=0
 try:
  while time.monotonic()-start<a.seconds:
   send(Event([6,19,20,18][i%4],source=1,part=8));i+=1;time.sleep(.05)
 finally:
  send(Event(5,source=1,flags=1))
  for _ in range(8):send(Event(19,source=1));send(Event(6,source=1,part=8));time.sleep(.05)
result={'status':'pending_checks','duration_seconds':a.seconds,'volume':20,'bad_crc':decoder.bad_crc,'status_frames':len(states),'singer_frames':len(singers),
 'identity':ids[-1] if ids else None,'panel_config':configs[-1] if configs else None,'transport_last':states[-1] if states else None,
 'singer_last':singers[-1] if singers else None,'max_active_voices':max((s['voices'] for s in states),default=0),
 'max_render_cycles':max((s['cycles'] for s in states),default=0),'playing_seen':any(s['playing'] for s in states),'physical_listening_confirmed':False,
 'c3_seat_owned_seen':any(s['owner']==2 for s in states),
 'panel_config_history':[dict(t) for t in {tuple(sorted(c.items())) for c in configs}]}
problems=[]
if not ids or any(x['build_id']!=audit['build_id'] or x['features']!=audit['features'] for x in ids):problems.append('identity')
if decoder.bad_crc:problems.append('UART CRC')
if not states or not result['playing_seen'] or states[-1]['playing'] or result['max_active_voices']==0:problems.append('transport/voices')
if any(s['deadline_miss'] or s['clips'] for s in states):problems.append('deadline/clipping')
if not singers or any(s['dropped'] or s['dac_dropped'] or s['dac_underruns'] for s in singers):problems.append('audio drops/underruns')
if not configs:problems.append('panel metadata')
result['status']='passed_digital_audition' if not problems else 'failed';result['problems']=problems
(b/'hardware_status.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
assert not problems,problems
