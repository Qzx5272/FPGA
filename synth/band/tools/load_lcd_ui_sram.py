"""Audit and load only the RGB LCD UI candidate into SRAM; never touch Flash."""
from pathlib import Path
import subprocess,sys,json,re,time,hashlib,argparse
parser=argparse.ArgumentParser();parser.add_argument('--build',default='D:/StarclusterBuilds/lcd_ui_20261031_a');parser.add_argument('--evidence',default='lcd_ui_20261031');args=parser.parse_args()
band=Path(__file__).resolve().parents[1];build=Path(args.build)
subprocess.run([sys.executable,str(band/'tools/audit_lcd_ui.py'),'--build',str(build),'--evidence',args.evidence],check=True)
out=band/'evidence'/args.evidence;audit=json.loads((out/'fpga_audit.json').read_text())
bit=build/'impl/pnr/phone_uart.fs';assert hashlib.sha256(bit.read_bytes()).hexdigest()==audit['bitstream_sha256']
cli='D:/Gowin/Gowin_V1.9.12.03_x64/Programmer/bin/programmer_cli.exe'
def run(args,name,timeout):
 p=subprocess.run([cli,*args],capture_output=True,text=True,errors='replace',timeout=timeout);s=p.stdout+p.stderr
 (out/(name+'.log')).write_text(s,encoding='utf-8')
 assert p.returncode==0 and not re.search(r'\b(error|failed|failure)\b',s,re.I),s
 return s
assert 'Cable found:' in run(['--scan-cables','F'],'scan',15)
base=['--device','GW5AST-138B','--cable-index','4','--location','0','--channel','0']
assert re.search(r'success|IDCODE|ID code',run(base+['--run','0'],'probe',15),re.I)
s=run(base+['--run','2','--fsFile',str(bit)],'sram',90)
assert re.search(r'success',s,re.I) or ('100%' in s and 'Finished.' in s)
(out/'sram_loaded.json').write_text(json.dumps({'bitstream_sha256':audit['bitstream_sha256'],'flash_written':False,'status':'loaded_identity_pending'},indent=2))
print('SRAM loaded; Flash unchanged. Querying real PC UART identity...',flush=True)
sys.path.insert(0,str(band/'host'));from protocol import Event,Decoder
import serial
decoder=Decoder();identity=None
with serial.Serial('COM12',1000000,timeout=.02) as port:
 deadline=time.monotonic()+5
 while time.monotonic()<deadline and identity is None:
  port.write(Event(18,source=1).encode_uart());time.sleep(.05)
  for p in decoder.feed(port.read(4096)):
   if p[1]==161:identity={'build_id':int.from_bytes(p[4:8],'little'),'features':int.from_bytes(p[20:24],'little')}
assert identity and identity['build_id']==audit['build_id'] and identity['features']==audit['features'],identity
identity['decoder_bad_crc']=decoder.bad_crc
(out/'pc_identity.json').write_text(json.dumps(identity,indent=2));print(json.dumps(identity,indent=2))
loaded=json.loads((out/'sram_loaded.json').read_text());loaded['status']='loaded_identity_verified';(out/'sram_loaded.json').write_text(json.dumps(loaded,indent=2))

