import sys,time,json,argparse,hashlib,datetime
from pathlib import Path
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
import serial
from protocol import Event,Decoder,status,singer_status,UART_GUARD_BYTES,UART_BATCH_SIZE
from shared_load_preflight import validate_shared_load
ap=argparse.ArgumentParser();ap.add_argument('--port',default='COM12');ap.add_argument('--release',type=Path,required=True);ap.add_argument('--seconds',type=float,default=97);ap.add_argument('--stress-seconds',type=float,default=30);ap.add_argument('--sound',action='store_true');ap.add_argument('--output',type=Path);ap.add_argument('--require-singer-health',action='store_true');ap.add_argument('--single-part-load',action='store_true',help='Require reviewed shared-bank source and hold256 note identities on choir part7');ap.add_argument('--exercise-load-controls',action='store_true',help='After sustained256 load, alternate expression32 times then require panic to clear all voices; telemetry latency only');args=ap.parse_args()
if args.seconds<=0 or args.stress_seconds<=0:ap.error('Durations must be positive')
output=args.output.resolve() if args.output else band/'evidence/hardware_band.json'
output.parent.mkdir(parents=True,exist_ok=True)
raw_output=output.with_suffix('.raw') if args.output else band/'evidence/hardware_uart.raw'
manifest=json.loads((args.release/'manifest.json').read_text(encoding='utf-8'))
bitstream_hash=hashlib.sha256((args.release/'starcluster_band.fs').read_bytes()).hexdigest()
if bitstream_hash!=manifest['bitstream_sha256'] or not manifest.get('build_id'):raise RuntimeError('A hashed release with a nonzero board build ID is required')
shared_preflight=validate_shared_load(args.release,manifest) if args.single_part_load else None
load_parts=[7] if args.single_part_load else list(range(8,15))+[7]
notes_per_part=256 if args.single_part_load else 32
records=[];decoder=Decoder();identity=None;verified=False;capture=bytearray()
result={'status':'running','started':datetime.datetime.now().isoformat(),'bitstream_sha256':bitstream_hash,'expected_build_id':manifest['build_id'],'audible_test_enabled':args.sound,'uart_guard_bytes':UART_GUARD_BYTES,'uart_max_batch_per_5ms':UART_BATCH_SIZE,'records':records}
result['test_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
result['shared_load_preflight']=shared_preflight
result['shared_load_preflight_sha256']=hashlib.sha256((Path(__file__).parent/'shared_load_preflight.py').read_bytes()).hexdigest()
result['require_singer_health']=args.require_singer_health
result['singer_health_checks']=0
result['stress_distribution']={'parts':load_parts,'notes_per_part':notes_per_part,'independent_serials':True,'scope':'Digital active slots; repeated32 pitches, not256 resolved spectral peaks or acoustic proof'}
output.with_suffix('.driver.txt').write_bytes(Path(__file__).read_bytes())
def checkpoint(stage):
 result['stage']=stage
 result['parser_bad_crc']=decoder.bad_crc
 # Bound checkpoint serialization time so observing a long test cannot starve
 # the 500 ms lease refresh. All samples are retained in the final record.
 snapshot=dict(result,records=records[-64:],record_count=len(records),checkpoint_records_truncated=len(records)>64)
 output.write_text(json.dumps(snapshot,indent=2))
 print(stage,flush=True)
with serial.Serial(args.port,1000000,timeout=.01,write_timeout=.1) as port:
 send_window=[time.monotonic(),0]
 def read_frames():
  block=port.read(1024);capture.extend(block);return decoder.feed(block)
 def send(e):
  elapsed=time.monotonic()-send_window[0]
  if e.kind!=127 and send_window[1]>=UART_BATCH_SIZE and elapsed<.005:time.sleep(.005-elapsed)
  if time.monotonic()-send_window[0]>=.005:send_window[:]=[time.monotonic(),0]
  raw=e.encode_uart()
  if port.write(raw)!=len(raw):raise IOError('Incomplete UART write')
  send_window[1]+=1
 def wait_for(predicate,part=4,source=1,timeout=2):
  start=time.monotonic();next_poll=0
  while time.monotonic()-start<timeout:
   if time.monotonic()>=next_poll:send(Event(6,source=source,part=part));next_poll=time.monotonic()+.03
   for frame in read_frames():
    if frame[1] not in (128,129):continue
    s=status(frame);s['time_monotonic']=time.monotonic();records.append(s)
    if s['part']==part and predicate(s):return s
  raise RuntimeError(f'Timeout waiting on part {part}; last={records[-1:]!r}')
 def check_health():
  if not args.require_singer_health:return
  until=time.monotonic()+2
  while time.monotonic()<until:
   send(Event(19,part=7));time.sleep(.02)
   for frame in read_frames():
    if frame[1]!=162:continue
    health=singer_status(frame)
    result['singer_health_checks']+=1;result['last_singer_health']=health
    if any(health[k] for k in ('dropped','dac_dropped','dac_underruns')):
     raise RuntimeError('Singer/DAC health error: '+repr(health))
    return
  raise RuntimeError('Missing singer/DAC health telemetry')
 try:
  # Read-only identity before any note, gain, transport or panic command.
  start=time.monotonic()
  while identity is None and time.monotonic()-start<3:
   send(Event(18))
   for raw in read_frames():
    if raw[1]==161:identity=dict(build_id=int.from_bytes(raw[4:8],'little'),capacity=int.from_bytes(raw[8:12],'little'),nominal_sample_rate=int.from_bytes(raw[12:16],'little'))
  if not identity or identity['build_id']!=manifest['build_id'] or identity['capacity']!=256:raise RuntimeError('Board identity does not match selected release: '+repr(identity))
  verified=True;result['identity']=identity;checkpoint('Identity matched; checking note ownership and releases')
  send(Event(127));send(Event(10,parameter=0));wait_for(lambda s:s['voices']==0)
  send(Event(4,part=4,flags=0));s=wait_for(lambda s:s['owner']==1);ep=s['epoch']
  send(Event(0,part=4,note=69,epoch=ep,serial=1));wait_for(lambda s:s['voices']==1)
  send(Event(1,part=4,note=69,epoch=ep,serial=999));time.sleep(.03);wait_for(lambda s:s['voices']==1)
  send(Event(0,part=4,note=72,epoch=ep,serial=2));wait_for(lambda s:s['voices']==2)
  send(Event(1,part=4,note=69,epoch=ep,serial=1));wait_for(lambda s:s['voices']==1)
  send(Event(1,part=4,note=72,epoch=ep,serial=2));wait_for(lambda s:s['voices']==0)
  for i in range(32):send(Event(0,part=4,contact=i,note=48+i,epoch=ep,serial=100+i,velocity=70))
  wait_for(lambda s:s['voices']==32)
  send(Event(2,part=4));wait_for(lambda s:s['voices']==0)
  send(Event(0,part=4,note=69,epoch=ep,serial=500));wait_for(lambda s:s['voices']==1)
  time.sleep(.7);wait_for(lambda s:s['voices']==0)
  # Held, nonzero sustain patches: eight quotas or one256-note shared role.
  # Master zero is a silent
  # control/timing test, not evidence of analog headroom or audible partials.
  send(Event(10,parameter=4 if args.sound else 0))
  for p in load_parts:
   send(Event(4,part=p));s=wait_for(lambda s:s['owner']==1,part=p);epoch=s['epoch']
   for parameter,value in ((0,127),(4,8192),(6,16383),(7,8)):send(Event(11,part=p,flags=parameter,parameter=value))
   for i in range(notes_per_part):send(Event(0,part=p,contact=i,note=40+i%32,velocity=100,epoch=epoch,serial=1000+p*32+i))
  wait_for(lambda s:s['voices']==256,part=7)
  stress_start=time.monotonic();maximum_cycles=0;next_checkpoint=0;next_health=0
  while time.monotonic()-stress_start<args.stress_seconds:
   s=wait_for(lambda s:True,part=7);maximum_cycles=max(maximum_cycles,s['cycles'])
   if s['voices']!=256 or s['deadline_miss'] or s['rejected'] or s['clips']:raise RuntimeError('Sustained load failed: '+repr(s))
   if time.monotonic()>=next_health:check_health();next_health=time.monotonic()+1
   if time.monotonic()>=next_checkpoint:
    checkpoint('256-slot sustained load: '+str(round(time.monotonic()-stress_start))+' seconds');next_checkpoint=time.monotonic()+30
   time.sleep(.02)
  if args.exercise_load_controls:
   # Keep the same active256 identities while exercising live expression.
   # Bounded UART pacing remains active; this is not an unbounded flood test.
   for change in range(32):
    send(Event(11,part=7,flags=0,parameter=96 if change%2==0 else 127))
   s=wait_for(lambda s:s['voices']==256,part=7)
   if any(s[k] for k in ('deadline_miss','rejected','clips')):raise RuntimeError('Load control errors: '+repr(s))
   sent=time.monotonic();send(Event(127))
   stopped=wait_for(lambda s:s['voices']==0 and not s['playing'],part=7)
   if any(stopped[k] for k in ('deadline_miss','rejected','clips')):raise RuntimeError('Panic control errors: '+repr(stopped))
   observed=time.monotonic()
   check_health()
   result['load_controls']={'status':'passed','expression_events':32,'active_slots_before_panic':s['voices'],
    'voices_after_panic':stopped['voices'],'panic_to_zero_telemetry_seconds':observed-sent,
    'scope':'Actual digital256 slots under bounded expression messages; response includes UART polling overhead, not input-to-audio latency or GUI backlog proof'}
   checkpoint('Full-load expression and panic passed')
  send(Event(2));wait_for(lambda s:s['voices']==0)
  send(Event(4,part=4,flags=1))
  for p in load_parts:send(Event(4,part=p,flags=1))
  # Restore the choir attack altered by the load test before judging the song.
  send(Event(11,part=7,flags=4,parameter=256))
  send(Event(10,parameter=32 if args.sound else 0));send(Event(5));wait_for(lambda s:s['playing']);checkpoint('Autonomous 96-second score running')
  for p in range(8):wait_for(lambda s:s['owner']==0,part=p)
  start=time.monotonic();maximum=0;furthest_sample=0;next_health=0
  while time.monotonic()-start<args.seconds:
   s=wait_for(lambda s:True);maximum=max(maximum,s['voices'])
   furthest_sample=max(furthest_sample,s['song_sample'])
   if s['deadline_miss'] or s['rejected'] or s['clips']:raise RuntimeError(f'Audio scheduling/capacity failure: {s}')
   if time.monotonic()>=next_health:check_health();next_health=time.monotonic()+1
   time.sleep(.05)
  if maximum==0:raise RuntimeError('Song produced no observed active voices')
  if args.seconds>=97 and (furthest_sample<4608000 or s['playing']):raise RuntimeError('The complete 96-second score did not reach its autonomous end')
  send(Event(5,flags=1));wait_for(lambda s:not s['playing'] and s['voices']==0)
  result.update(status='passed',configuration='PT8211 audition build',automatic_test_seconds=args.seconds,stress_seconds=args.stress_seconds,stress_active_notes=256,maximum_stress_cycles=maximum_cycles,maximum_observed_voices_during_song=maximum,furthest_song_sample=furthest_sample,parser_bad_crc=decoder.bad_crc,tests=['build identity match','ownership','independent same-contact serial identities','stale release','32 active slots','source release','500ms disconnect release','256 sustained active slots','autonomous song','stop'])
  if decoder.bad_crc:raise RuntimeError('Telemetry CRC integrity failed: '+str(decoder.bad_crc))
 except Exception as e:
  result.update(status='failed',error=str(e));raise
 finally:
  result['stage']='completed' if result['status']=='passed' else 'failed'
  result['completed']=datetime.datetime.now().isoformat()
  result['parser_bad_crc']=decoder.bad_crc
  if verified:
   try:send(Event(127));send(Event(10,parameter=0))
   except Exception as e:result.update(status='failed',stage='failed',cleanup_error=str(e))
  output.write_text(json.dumps(result,indent=2))
  raw_output.write_bytes(capture)
print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
if result['status']!='passed':raise SystemExit(1)
