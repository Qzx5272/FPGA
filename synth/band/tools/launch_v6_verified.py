"""Leave the real V6 GUI open and record its identity/stopped startup state."""
from pathlib import Path
import argparse,datetime,json,sys,time
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from app import QApplication,Desk,QTimer
from protocol import Event
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--port',default='COM12');ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
selected=json.loads((band/'CURRENT_RELEASE.json').read_text(encoding='utf-8'))
app=QApplication([]);desk=Desk();desk.show();desk.ports.setCurrentText(args.port);desk.connect_port();desk.open_workstation()
started=time.monotonic();silenced=None;reported=False
def check():
 global silenced,reported
 if reported:return
 now=time.monotonic();identity=desk.board_identity
 if identity and identity['build_id']==selected['build_id'] and silenced is None:
  desk.panic();desk.enqueue(Event(5,flags=1));desk.volume.setValue(0);desk.enqueue(Event(10,parameter=0));silenced=now
 state=desk.states.get(desk.part.currentIndex(),{})
 passed=silenced is not None and now-silenced>=1 and state.get('_received',0)>silenced and state.get('voices')==0 and not state.get('playing') and desk.decoder.bad_crc==0
 if passed or now-started>15:
  record=dict(status='passed' if passed else 'failed',at=datetime.datetime.now().isoformat(),expected_build=selected['build_id'],
   identity=identity,state=state,window_title=desk.windowTitle(),workstation_visible=desk.workstation.isVisible(),
   master_zero_sent=silenced is not None,master_slider=desk.volume.value(),bad_crc=desk.decoder.bad_crc,
   scope='Actual desktop GUI and UART startup; no gain readback, acoustic or physical peripheral measurement')
  args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(record,indent=2),encoding='utf-8')
  if passed:
   folder=args.output.parent/'screenshots';folder.mkdir(exist_ok=True)
   desk.grab().save(str(folder/'desk_final.png'));desk.workstation.grab().save(str(folder/'workstation_final.png'))
  reported=True
timer=QTimer();timer.timeout.connect(check);timer.start(100)
sys.exit(app.exec())
