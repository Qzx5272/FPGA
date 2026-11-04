"""Synthesize the calibrated input frontend; resource evidence only, never program."""
from pathlib import Path
import hashlib,json,subprocess,sys,datetime,shutil
b=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else b/'experimental/stage/stage_pad_frontend.sv'
assert source.name=='stage_pad_frontend.sv'
digest=hashlib.sha256(source.read_bytes()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('stage_pad_syn_'+digest)
if target.exists():raise RuntimeError('Preserve existing build '+str(target))
target.mkdir();shutil.copy2(source,target/source.name)
(target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module stage_pad_frontend
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
add_file stage_pad_frontend.sv
set_option -output_base_name stage_pad
run syn
''')
out=b/'evidence/stage_pad_synthesis'/digest;out.mkdir(parents=True,exist_ok=False)
record=dict(status='running',build=str(target),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
 scope='Standalone default10ADC-lane/64pad synthesis;no physical resources,timing,or board acceptance',started=datetime.datetime.now().isoformat())
report=out/'result.json';report.write_text(json.dumps(record,indent=2))
try:
 with (target/'build.log').open('w') as log:
  p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=600)
 record['returncode']=p.returncode
 if p.returncode or 'ERROR' in (target/'build.log').read_text():raise RuntimeError('Vendor synthesis failed')
 if not (target/'impl/gwsynthesis/stage_pad.vg').exists():raise RuntimeError('Missing synthesized netlist')
 record['status']='passed_synthesis_only'
except Exception as error:
 record.update(status='failed',error=str(error));raise
finally:
 for f in (target/'impl/gwsynthesis').glob('*.html'):shutil.copy2(f,out/f.name)
 for name in ('build.tcl','build.log','stage_pad_frontend.sv'):shutil.copy2(target/name,out/name)
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
