"""Keep the board silent, applying controls only after the expected build ID."""
from pathlib import Path
import argparse,datetime,json,sys,time
import serial
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from protocol import Event,Decoder,status

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--port',default='COM12',help='UART connected to the fixed-pin FPGA shell')
ap.add_argument('--build-id',type=lambda v:int(v,0),required=True)
ap.add_argument('--timeout',type=float,default=240)
ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--completion-record',type=Path,help='Keep guarding through programming; require a fresh identity after this Flash operation completes')
a=ap.parse_args()
if a.output.exists():raise FileExistsError(a.output)
decoder=Decoder();record={'status':'waiting_for_expected_identity','started':datetime.datetime.now().isoformat(),
 'expected_build_id':a.build_id,'controls_sent':False,'scope':'Digital UART control only; no gain readback or acoustic measurement'}
a.output.parent.mkdir(parents=True,exist_ok=True)
with serial.Serial(a.port,1000000,timeout=.01,write_timeout=.1) as port:
 end=time.monotonic()+a.timeout;next_query=0;next_silence=0;matched=False;stopped=False
 completed=a.completion_record is None
 while time.monotonic()<end:
  now=time.monotonic()
  if not completed and a.completion_record.exists():
   try:operation=json.loads(a.completion_record.read_text(encoding='utf-8'))
   except (ValueError,OSError):operation={}
   if operation.get('status')=='flash_verified_reload_returned_pending_uart':
    completed=True;matched=False;stopped=False;record['controls_sent']=False
    decoder=Decoder();port.reset_input_buffer();next_query=0;next_silence=0
    record['after_flash_reload']=True
  if not matched and now>=next_query:
   port.write(Event(18).encode_uart());next_query=now+.1
  if matched and (not stopped or not completed) and now>=next_silence:
   for event in (Event(5,flags=1),Event(127),Event(10,parameter=0)):
    port.write(event.encode_uart())
   record['controls_sent']=True
   next_silence=now+.1
  for frame in decoder.feed(port.read(4096)):
   if frame[1]==161:
    observed=int.from_bytes(frame[4:8],'little')
    if observed!=a.build_id:continue
    matched=True;record['identity']={'build_id':observed,'capacity':int.from_bytes(frame[8:12],'little'),
      'features':int.from_bytes(frame[20:24],'little')}
   elif matched and record['controls_sent'] and frame[1] in (128,129):
    state=status(frame);record['last_state']=state
    if not state['playing'] and state['voices']==0:stopped=True
  if completed and stopped and time.monotonic()-next_silence>2:break
if not completed:record.update(status='failed',error='Flash completion was not observed')
elif not matched:record.update(status='failed',error='Expected FPGA identity was not observed')
elif not stopped:record.update(status='failed',error='No stopped/zero-voice telemetry after silence commands')
else:record.update(status='passed',master_zero_sent=True)
record['bad_crc']=decoder.bad_crc;record['finished']=datetime.datetime.now().isoformat()
a.output.write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
if record['status']!='passed':raise SystemExit(1)
