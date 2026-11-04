"""Exercise real GUI observer polling; no play, gain, or note-on commands."""
from pathlib import Path
import sys,os,time,json,hashlib,datetime
os.environ['QT_QPA_PLATFORM']='offscreen'
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from app import QApplication,Desk
app=QApplication([]);desk=Desk();desk.ports.setCurrentText('COM12')
record=dict(status='running',started=datetime.datetime.now().isoformat(),scope='Live GUI16-part ownership polling and stale display; not physical performance or audio',
            sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (band/'host').glob('*.py')})
target=band/'evidence/hardware_stage.json';target.write_text(json.dumps(record,indent=2))
try:
    desk.connect_port()
    if desk.port is None:raise RuntimeError(desk.info.text())
    desk.open_stage()
    until=time.monotonic()+8
    while time.monotonic()<until:app.processEvents();time.sleep(.002)
    selected=json.loads((band/'CURRENT_RELEASE.json').read_text())
    if not desk.board_identity or desk.board_identity['build_id']!=selected['build_id']:raise RuntimeError('Current band identity not confirmed')
    snapshot=desk.stage_state.snapshot(time.monotonic(),True)
    if not snapshot['live'] or any(o is None for o in snapshot['owners']):raise RuntimeError('Not all16 tracks have fresh telemetry')
    if desk.decoder.bad_crc:raise RuntimeError('CRC errors: '+str(desk.decoder.bad_crc))
    record.update(identity=desk.board_identity,live_snapshot=snapshot,queue_depth=len(desk.queue),bad_crc=desk.decoder.bad_crc)
    desk.stage_view.refresh();desk.stage_view.grab().save(str(band/'evidence/ui/stage_board_live.png'))
    desk.connect_port();desk.stage_view.refresh()
    if desk.stage_state.snapshot(time.monotonic(),False)['live']:raise RuntimeError('Stale board marked live after disconnect')
    record['status']='passed'
except Exception as exc:
    record.update(status='failed',error=str(exc));raise
finally:
    record.update(last_identity=desk.board_identity,observed_tracks=sorted(desk.stage_state.tracks),bad_crc=desk.decoder.bad_crc)
    desk.close();record['finished']=datetime.datetime.now().isoformat();target.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
