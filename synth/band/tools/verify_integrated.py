"""Reproducible offline release checks; never accesses attached hardware."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,shutil,time
p=argparse.ArgumentParser();p.add_argument('--build',required=True);a=p.parse_args()
b=Path(a.build).resolve();root=Path(__file__).resolve().parents[3];band=root/'synth/band'
cad=root/'tmp/oss-cad-suite';env=dict(os.environ);env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH']
out=b/'verification';out.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((b/'manifest.json').read_text())
for n,h in manifest['source_sha256'].items():assert sha(b/n)==h,('source drift',n)
tests={'adc':['adc_voltage_parser.sv'],'audio':['audio48_duplex.sv'],'buffer':['event_packet_buffer.sv'],'lcd':['lcd_output_stage.sv'],
 'panel':['panel_integrated.sv','input_filter.sv','quadrature_encoder.v'],
 'engine':[p.name for p in (b/'rtl').iterdir() if p.suffix in ('.v','.sv') and not p.name.startswith('tb_')]}
if manifest['build_id']>=0x20261103:tests['status_wire']=['status_sender.v','uart.v']
if manifest['build_id']>=0x20261104:
 tests['selection']=tests['engine']
 pins=json.loads((b/'pins.json').read_text())
 for port,ball in [('enc_a[0]','AB25'),('enc_b[0]','AB26'),('enc_sw_n[0]','P23'),('enc_sw_n[1]','P24')]:
  assert pins[port]['ball']==ball,(port,ball)
if manifest['build_id']>=0x20261107:
 tests['strip']=['rhythm_strip.sv']
 tests['analysis']=tests['engine']
 tests['workstation_panel']=tests.pop('panel')+['encoder_press.sv']
 tests['workstation_engine']=tests.pop('engine')
results=[]
for name,files in tests.items():
 tb=band/'tests'/f'tb_integrated_{name}.sv';exe=out/f'{name}.vvp';start=time.monotonic()
 command=[str(cad/'bin/iverilog.exe'),'-g2012','-i','-I',str(b/'rtl'),'-s','tb','-o',str(exe),str(tb),*[str(b/'rtl'/f) for f in files]]
 if not manifest.get("external_panel_keys",True):command.insert(1,"-DNO_EXTERNAL_PANEL_KEYS")
 c=subprocess.run(command,env=env,capture_output=True,text=True,timeout=120)
 (out/f'{name}_compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
 r=subprocess.run([str(cad/'bin/vvp.exe'),str(exe)],cwd=b,env=env,capture_output=True,text=True,timeout=300)
 (out/f'{name}.log').write_text(r.stdout+r.stderr)
 assert r.returncode==0 and 'PASS' in r.stdout,(name,r.stdout,r.stderr)
 results.append({'test':name,'status':'passed','seconds':round(time.monotonic()-start,2),'fixture_sha256':sha(tb),'output':r.stdout.strip()})
 print(r.stdout.strip(),flush=True)
cpp=band/'bridges/esp32c3_pad/test_pad_fpga.cpp';exe=out/'pad_test.exe'
compiler=shutil.which('g++') or 'C:/mingw64/bin/g++.exe'
c=subprocess.run([compiler,'-std=c++17','-Wall','-Wextra',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=120)
(out/'c3_compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
(out/'c3.log').write_text(r.stdout+r.stderr);assert r.returncode==0 and 'PASS' in r.stdout,r.stdout+r.stderr
results.append({'test':'c3','status':'passed','fixture_sha256':sha(cpp),'implementation_sha256':sha(cpp.parent/'src/pad_fpga.h'),'output':r.stdout.strip()})
lesson=cpp.parent/'test_pad_lesson.cpp'
if lesson.exists():
 exe=out/'pad_lesson.exe'
 subprocess.run([compiler,'-std=c++17','-I',str(cpp.parent/'tests/stubs'),str(lesson),'-o',str(exe)],check=True,timeout=120)
 r=subprocess.run([str(exe)],capture_output=True,text=True,check=True,timeout=15)
 assert 'PASS' in r.stdout
 (out/'lesson.log').write_text(r.stdout)
 results.append({'test':'lesson','status':'passed','implementation_sha256':sha(cpp.parent/'src/pad_lesson.h'),'fixture_sha256':sha(lesson),'output':r.stdout.strip()})
ui=(b/'ui_test.log').read_text();assert 'PASS four UI pages' in ui
results.append({'test':'ui','status':'passed','output':ui.strip(),'fixture_sha256':sha(b/'ui_test.sv')})
(b/'verification.json').write_text(json.dumps({'status':'passed','build_id':manifest['build_id'],'hardware_accessed':False,'tests':results},indent=2))
print('PASS offline release checks; hardware validation remains separate')
