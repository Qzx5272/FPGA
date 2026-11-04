"""Audited SRAM-only load followed by a real UART identity check."""
from pathlib import Path
import argparse,subprocess,sys,re,json,time,hashlib
p=argparse.ArgumentParser();p.add_argument('--build',required=True);p.add_argument('--port',default='COM12');p.add_argument('--cable-index',default='4');a=p.parse_args()
b=Path(a.build).resolve();band=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(band/'tools/audit_integrated.py'),'--build',str(b)],check=True)
audit=json.loads((b/'audit.json').read_text());bit=b/'impl/pnr/integrated.fs'
assert hashlib.sha256(bit.read_bytes()).hexdigest()==audit['bitstream_sha256']
logs=b/'hardware_logs';logs.mkdir(exist_ok=True)
cli='D:/Gowin/Gowin_V1.9.12.03_x64/Programmer/bin/programmer_cli.exe'
def run(args,name,timeout):
 r=subprocess.run([cli,*args],capture_output=True,text=True,errors='replace',timeout=timeout)
 text=r.stdout+r.stderr;(logs/(name+'.log')).write_text(text,encoding='utf-8')
 assert r.returncode==0 and not re.search(r'\b(error|failed|failure)\b',text,re.I),text
 return text
assert 'Cable found:' in run(['--scan-cables','F'],'scan',15)
target=['--device','GW5AST-138B','--cable-index',a.cable_index,'--location','0','--channel','0']
assert re.search(r'success|IDCODE|ID code',run(target+['--run','0'],'probe',15),re.I)
text=run(target+['--run','2','--fsFile',str(bit)],'sram',90)
assert re.search(r'success',text,re.I) or ('100%' in text and 'Finished.' in text)
loaded={'status':'loaded_identity_pending','bitstream_sha256':audit['bitstream_sha256'],'flash_written':False}
(b/'sram_loaded.json').write_text(json.dumps(loaded,indent=2))
sys.path.insert(0,str(band/'host'));from protocol import Event,Decoder
import serial
d=Decoder();identity=None;replies=[]
with serial.Serial(a.port,1000000,timeout=.02) as port:
 settle=time.monotonic()+.3
 while time.monotonic()<settle:port.read(4096)
 port.reset_input_buffer()
 end=time.monotonic()+6
 while time.monotonic()<end and identity is None:
  port.write(Event(18,source=1).encode_uart());time.sleep(.05)
  for payload in d.feed(port.read(4096)):
   if payload[1]==161:identity={'build_id':int.from_bytes(payload[4:8],'little'),'features':int.from_bytes(payload[20:24],'little')}
assert identity and identity['build_id']==audit['build_id'] and identity['features']==audit['features'],identity
identity['bad_crc']=d.bad_crc;(b/'pc_identity.json').write_text(json.dumps(identity,indent=2))
loaded['status']='loaded_identity_verified';(b/'sram_loaded.json').write_text(json.dumps(loaded,indent=2))
print(json.dumps(loaded,indent=2));print(json.dumps(identity,indent=2))
