"""Program/verify boot Flash only after this exact image passed SRAM identity."""
from pathlib import Path
import argparse,subprocess,sys,json,re,time,hashlib
p=argparse.ArgumentParser();p.add_argument('--build',required=True);p.add_argument('--port',default='COM12');a=p.parse_args()
b=Path(a.build).resolve();band=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(band/'tools/audit_integrated.py'),'--build',str(b)],check=True)
audit=json.loads((b/'audit.json').read_text());loaded=json.loads((b/'sram_loaded.json').read_text());identity=json.loads((b/'pc_identity.json').read_text())
assert loaded['status']=='loaded_identity_verified' and loaded['bitstream_sha256']==audit['bitstream_sha256']
assert identity['build_id']==audit['build_id'] and identity['features']==audit['features']
bit=b/'impl/pnr/integrated.fs';assert hashlib.sha256(bit.read_bytes()).hexdigest()==audit['bitstream_sha256']
logs=b/'hardware_logs';logs.mkdir(exist_ok=True)
cli='D:/Gowin/Gowin_V1.9.12.03_x64/Programmer/bin/programmer_cli.exe'
base=['--device','GW5AST-138B','--cable-index','4','--location','0','--channel','0','--frequency','0.5MHz']
record={'status':'programming','bitstream_sha256':audit['bitstream_sha256'],'flash_may_be_modified':True,'flash_written':False,'cold_power_cycle_verified':False}
def save():(b/'flash_operation.json').write_text(json.dumps(record,indent=2))
def run(args,name,timeout,success):
 command=[cli,*base,*args];(logs/(name+'.command.json')).write_text(json.dumps(command))
 with (logs/(name+'.log')).open('w',encoding='utf-8') as log:
  result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 text=(logs/(name+'.log')).read_text(errors='replace')
 assert result.returncode==0 and not re.search(r'\b(error|failed|failure)\b',text,re.I) and re.search(success,text,re.I),text[-2000:]
run(['--run','0'],'flash_probe',20,r'ID Code is: 0x0001081B')
save();print('Programming and verifying boot Flash...',flush=True)
try:
 run(['--run','54','--fsFile',str(bit)],'flash_program_verify',600,r'Program and Verify Flash successfully')
 record.update(status='verified_reload_pending',flash_written=True);save()
 run(['--run','1'],'flash_reload',30,r'success|Finished\.')
 sys.path.insert(0,str(band/'host'));from protocol import Event,Decoder
 import serial
 d=Decoder();found=None
 with serial.Serial(a.port,1000000,timeout=.02) as port:
  settle=time.monotonic()+.3
  while time.monotonic()<settle:port.read(4096)
  port.reset_input_buffer();end=time.monotonic()+8
  while time.monotonic()<end and found is None:
   port.write(Event(18,source=1).encode_uart());time.sleep(.05)
   for raw in d.feed(port.read(4096)):
    if raw[1]==161:found={'build_id':int.from_bytes(raw[4:8],'little'),'features':int.from_bytes(raw[20:24],'little')}
 assert found and found['build_id']==audit['build_id'] and found['features']==audit['features'],found
 record.update(status='flash_verified_reload_identity_passed',identity=found,bad_crc=d.bad_crc);save()
 (b/'flash_loaded.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
except Exception as e:
 record.update(status='failed',error=str(e));save();raise
