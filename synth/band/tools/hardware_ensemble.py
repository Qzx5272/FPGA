"""Full-song real-board GUI collaboration test with synthetic seats, master=0.
Does not substitute for real MIDI hardware, physical latency, or listening.
"""
import os,sys,time,json,hashlib,datetime,argparse
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--release',type=Path)
ap.add_argument('--output',type=Path)
ap.add_argument('--require-singer-health',action='store_true')
ap.add_argument('--vision-selector',action='store_true',help='Synthetic marker frames through actual GUI mapping; no camera capture')
args=ap.parse_args()
selected=json.loads(((args.release/'manifest.json') if args.release else (band/'CURRENT_RELEASE.json')).read_text(encoding='utf-8'))
if args.release:
    if hashlib.sha256((args.release/'starcluster_band.fs').read_bytes()).hexdigest()!=selected['bitstream_sha256']:
        raise RuntimeError('Release hash mismatch')
from app import QApplication,Desk
from protocol import Event
app=QApplication([]);desk=Desk();desk.ports.setCurrentText('COM12')
path=args.output or band/'evidence/hardware_ensemble.json';records=[];checks=[];verified=False
path.parent.mkdir(parents=True,exist_ok=True)
result=dict(status='running',started=datetime.datetime.now().isoformat(),scope='Actual FPGA and GUI, synthetic seats, silent master; no physical MIDI or audio acceptance',
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (band/'host').glob('*.py')},records=records,checks=checks,
    bitstream_sha256=selected['bitstream_sha256'],test_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    require_singer_health=args.require_singer_health,singer_health=[],vision_selector=args.vision_selector,vision_steps=[])
if args.vision_selector:
    result['scope']+='; synthetic red-marker frames through visual dwell/confirmation, not real camera recognition'
def save():path.write_text(json.dumps(result,indent=2))
def step():app.processEvents();time.sleep(.003)
def wait(predicate,label,timeout=4):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        step()
        if predicate():checks.append(label);print(label,flush=True);return
    raise RuntimeError('Timeout: '+label)
def owner(part):return desk.states.get(part,{}).get('owner')
def current():return desk.stage_state.latest or {}

def select_from_marker(seat,part,expected=True):
    from vision_control import VisionControl
    from PySide6.QtGui import QImage,QColor
    if desk.vision_control is None:desk.vision_control=VisionControl(desk)
    vision=desk.vision_control;vision.stop();vision.seat.setValue(seat);vision.running=True
    image=QImage(96,64,QImage.Format.Format_RGBA8888);image.fill(QColor('black'))
    cx=12+(part%4)*24;cy=16+(part//4)*32
    for y in range(cy-3,cy+3):
        for x in range(cx-3,cx+3):image.setPixelColor(x,y,QColor(240,20,20))
    before=desk.seat_parts[seat];started=time.monotonic();next_frame=started
    try:
        while time.monotonic()-started<1.05:
            now=time.monotonic()
            if now>=next_frame:vision.process_image(image,now);next_frame=now+.08
            step()
        if vision.camera is not None or vision.gate.candidate(time.monotonic())!=part:
            raise RuntimeError('Synthetic vision failed dwell or unexpectedly opened a camera')
        vision.accept_candidate()
        if expected:
            if desk.seat_parts[seat]!=part or vision.gate.part is not None:
                raise RuntimeError('Vision confirmation did not apply and consume candidate')
        elif desk.seat_parts[seat]!=before or vision.gate.part!=part:
            raise RuntimeError('Vision conflict was not rejected')
        result['vision_steps'].append(dict(seat=seat,part=part,expected_accept=expected,
            previous_mapping=before,result_mapping=desk.seat_parts[seat],camera_opened=False,
            elapsed=time.monotonic()-started,message=vision.message.text()))
    finally:vision.stop()

try:
    save();desk.connect_port();desk.open_stage()
    wait(lambda:desk.board_identity is not None,'identity response')
    if desk.board_identity['build_id']!=selected['build_id']:raise RuntimeError('Unexpected firmware')
    verified=True;result['identity']=desk.board_identity
    if args.require_singer_health and not desk.board_identity.get('features',0)&32:
        raise RuntimeError('Singer health telemetry not supported')
    desk.panic();desk.volume.setValue(0);desk.start_performance()
    wait(lambda:current().get('playing',False),'autonomous score running')
    if args.vision_selector:
        select_from_marker(2,3);select_from_marker(3,6)
        wait(lambda:owner(3)==0 and owner(6)==0,'visual mapping alone leaves FPGA tracks with machine')
    start=time.monotonic();actions=set();last_record=0;previous=0;maximum=0
    while time.monotonic()-start<98:
        step();elapsed=time.monotonic()-start;s=current()
        if elapsed>=2 and 'take' not in actions:
            if args.vision_selector:
                desk.press(12,43,100,source=2);desk.press(13,72,100,source=3)
            else:
                desk.press(12,43,100,source=2,part=3);desk.press(13,72,100,source=3,part=6)
            wait(lambda:owner(3)==2 and owner(6)==3 and all(n['sent'] for n in desk.held.values()),'two simultaneous human owners and notes sent')
            if owner(0)!=0:raise RuntimeError('Unrelated drum track ownership changed')
            if args.vision_selector:
                select_from_marker(4,3,expected=False)
                checks.append('visual selector rejected another live FPGA track owner')
            desk.press(14,48,100,source=4,part=3)
            if (4,14) in desk.held:raise RuntimeError('GUI accepted conflicting owner')
            checks.append('conflicting seat blocked by GUI');actions.add('take')
        if elapsed>=7 and 'return' not in actions:
            desk.release(12,source=2)
            wait(lambda:owner(3)==0 and owner(6)==3,'bass returned while lead remains human')
            actions.add('return')
        if elapsed>=12 and 'lost' not in actions:
            # Remove only simulated input bookkeeping. No release command: the
            # FPGA must expire seat3's lease and return its track at a bar.
            desk.held.pop((3,13));desk.queue=type(desk.queue)(e for e in desk.queue if e.source!=3)
            wait(lambda:owner(6)==0,'lost source lease returned lead to machine')
            actions.add('lost')
        if elapsed>=18 and 'rejoin' not in actions:
            desk.press(15,76,90,source=3,part=6)
            wait(lambda:owner(6)==3 and desk.held[(3,15)]['sent'],'seat rejoins and new note sent')
            desk.release(15,source=3);wait(lambda:owner(6)==0,'rejoined seat returns on bar');actions.add('rejoin')
        if elapsed-last_record>=.1:
            last_record=elapsed;s=dict(current());sample=s.get('song_sample',0)
            if sample<previous:raise RuntimeError('Score position moved backward')
            previous=sample;maximum=max(maximum,s.get('voices',0))
            if any(s.get(k,0) for k in ('deadline_miss','clips','rejected')):raise RuntimeError('Board audio/control error: '+repr(s))
            if args.require_singer_health and elapsed>=1:
                health=desk.singer_snapshot
                if health is None or time.monotonic()-desk.singer_received>2.5:
                    raise RuntimeError('Missing/stale singer and DAC telemetry')
                if any(health.get(k,0) for k in ('dropped','dac_dropped','dac_underruns')):
                    raise RuntimeError('Singer/DAC error: '+repr(health))
                result['singer_health'].append(dict(elapsed=elapsed,**health))
            records.append(dict(elapsed=elapsed,**s))
        if elapsed>=30 and 'checkpoint30' not in actions:save();print('30-second score checkpoint',flush=True);actions.add('checkpoint30')
        if elapsed>=60 and 'checkpoint60' not in actions:save();print('60-second score checkpoint',flush=True);actions.add('checkpoint60')
    if previous!=4608000 or current().get('playing') or maximum==0:raise RuntimeError('Full score did not complete')
    if desk.decoder.bad_crc:raise RuntimeError('Telemetry CRC failed')
    checks.append('96-second score reached natural end during GUI polling')
    result.update(status='passed',song_sample=previous,peak_global_voices=maximum,bad_crc=desk.decoder.bad_crc)
except Exception as exc:result.update(status='failed',error=str(exc));raise
finally:
    cleanup_errors=[]
    try:
        if verified:
            desk.panic();desk.enqueue(Event(10,parameter=0))
            until=time.monotonic()+.3
            while time.monotonic()<until:step()
    except Exception as exc:cleanup_errors.append('panic/silence: '+str(exc))
    try:desk.close()
    except Exception as exc:cleanup_errors.append('close: '+str(exc))
    if cleanup_errors:
        result.update(status='failed',cleanup_errors=cleanup_errors)
    result['finished']=datetime.datetime.now().isoformat();save()
print(json.dumps({k:v for k,v in result.items() if k not in ('records','sources','singer_health')},indent=2))
if result['status']!='passed':raise SystemExit(1)
