"""Short silent real-board check of V6 preset selection and event recording/replay."""
import argparse,datetime,json,os,sys,time
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from app import QApplication,Desk
from protocol import Event
from performance_recording import save,load
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--release',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--port',default='COM12');args=ap.parse_args()
manifest=json.loads((args.release/'manifest.json').read_text(encoding='utf-8'))
if args.output.exists():raise FileExistsError(args.output)
args.output.parent.mkdir(parents=True,exist_ok=True)
app=QApplication([]);desk=Desk();verified=False;checks=[]
result=dict(status='running',started=datetime.datetime.now().isoformat(),checks=checks,
 scope='Real FPGA UART with actual Qt controller, synthetic notes, master zero; not listening or physical pad verification')
def step():app.processEvents();time.sleep(.003)
def dwell(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:step()
def wait(predicate,label,timeout=5):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  step()
  if predicate():checks.append(label);print(label,flush=True);return
 raise RuntimeError('Timeout: '+label)
def state():return desk.stage_state.latest or {}
def silence():
 desk.panic();desk.enqueue(Event(5,flags=1));desk.volume.setValue(0);desk.enqueue(Event(10,parameter=0))
 dwell(.25)
 wait(lambda:state().get('voices')==0 and not state().get('playing'),'stopped zero-voice readback')
try:
 desk.ports.setCurrentText(args.port);desk.connect_port();desk.open_stage();desk.open_workstation()
 wait(lambda:desk.board_identity is not None,'identity received')
 if desk.board_identity['build_id']!=manifest['build_id']:raise RuntimeError('Unexpected build ID')
 verified=True;result['identity']=desk.board_identity
 if not desk.board_identity['features']&64:raise RuntimeError('New algorithm presets not supported by this build')
 silence();w=desk.workstation;w.family.setCurrentText('全部')
 for preset in ('pluck','flute','kick','bell'):
  silence();w.presets.setCurrentIndex(w.presets.findData(preset));w.apply_preset()
  source=desk.source();desk.press(120,60,90,source)
  wait(lambda:desk.held.get((source,120),{}).get('sent') and state().get('voices',0)>0,'preset '+preset+' scheduled on FPGA')
  dwell(.12);desk.release(120,source)
 silence();desk.part.setCurrentIndex(6);source=desk.source();dwell(.2)
 w.start_recording();desk.press(121,64,91,source)
 wait(lambda:desk.held.get((source,121),{}).get('sent') and state().get('voices',0)>0,'recorded live note active')
 old_serial=desk.held[(source,121)]['serial'];desk.parameter(0,83);dwell(.5)
 desk.release(121,source);dwell(.4);w.stop_recording()
 if not {0,1,11}.issubset({e['event']['kind'] for e in w.take['events']}):raise RuntimeError('Take lost notes or control actions')
 take_path=args.output.with_suffix('.take.json');save(take_path,w.take);w.take=load(take_path)
 checks.append('take saved and loaded with note, velocity, release and control events')
 silence();start=time.monotonic();w.start_playback()
 wait(lambda:w.player.active and any(n['sent'] for n in desk.held.values()) and state().get('voices',0)>0,'saved take replay active on FPGA')
 new_serials=[n['serial'] for n in desk.held.values()]
 if old_serial in new_serials:raise RuntimeError('Replay reused stale note serial')
 wait(lambda:not w.player.active and w.replay_wait is None and w.pending_return is None,'saved take replay finished',timeout=8)
 result.update(recording_events=len(w.take['events']),take=str(take_path),old_serial=old_serial,replay_serials=new_serials,
  replay_seconds=time.monotonic()-start,bad_crc=desk.decoder.bad_crc)
 if desk.decoder.bad_crc:raise RuntimeError('UART CRC errors')
 health=desk.singer_snapshot
 if health is None or any(health.get(k,0) for k in ('dropped','dac_dropped','dac_underruns')):raise RuntimeError('Missing/failed DAC health')
 result['health']=health;silence();result['last_state']=state();result['status']='passed'
except Exception as exc:
 result.update(status='failed',error=str(exc));raise
finally:
 try:
  if verified:silence()
  desk.close()
 except Exception as exc:result.update(status='failed',cleanup_error=str(exc))
 result['finished']=datetime.datetime.now().isoformat();args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
if result['status']!='passed':raise SystemExit(1)
