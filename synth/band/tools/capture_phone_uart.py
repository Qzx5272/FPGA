"""Passively capture phone-triggered FPGA replies; never transmit PC commands."""
import argparse,json,sys,time
from pathlib import Path
import serial
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from protocol import Decoder,status
p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=120);p.add_argument('--output',required=True);a=p.parse_args()
d=Decoder();counts={};last=None
with serial.Serial('COM12',1000000,timeout=.1) as s,Path(a.output).open('w',encoding='utf-8') as f:
 end=time.monotonic()+a.seconds
 while time.monotonic()<end:
  for raw in d.feed(s.read(4096)):
   counts[str(raw[1])]=counts.get(str(raw[1]),0)+1
   r={'time':time.time(),'kind':raw[1]}
   if raw[1] in (128,129):r.update(status(raw))
   elif raw[1]==161:r.update(build_id=int.from_bytes(raw[4:8],'little'),features=int.from_bytes(raw[20:24],'little'))
   f.write(json.dumps(r)+'\n');f.flush()
   key=(r.get('playing'),r.get('owner'),r.get('voices'))
   if key!=last:print(json.dumps(r),flush=True);last=key
 result={'passive':True,'frames':counts,'bad_crc':d.bad_crc}
 f.write(json.dumps(result)+'\n');print(json.dumps(result),flush=True)
