"""Synthesize the spectrum pixel consumer; resource evidence only, never program."""
from pathlib import Path
import hashlib,json,subprocess,sys,datetime,shutil
b=Path(__file__).resolve().parents[1]
source=b/'experimental/audio_visual/spectrum_bars.v'
digest=hashlib.sha256(source.read_bytes()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('spectrum_bars_syn_'+digest)
if target.exists():raise RuntimeError('Preserve existing build '+str(target))
target.mkdir();shutil.copy2(source,target/source.name)
(target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module spectrum_bars
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
add_file spectrum_bars.v
set_option -output_base_name spectrum_bars
run syn
''')
out=b/'evidence/spectrum_bars_synthesis'/digest;out.mkdir(parents=True,exist_ok=False)
record=dict(status='running',build=str(target),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
 scope='Standalone spectrum pixel consumer synthesis;no fulltop,video timing,HDMI or physical acceptance',started=datetime.datetime.now().isoformat())
report=out/'result.json';report.write_text(json.dumps(record,indent=2))
try:
 with (target/'build.log').open('w') as log:
  p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=600)
 record['returncode']=p.returncode
 if p.returncode or 'ERROR' in (target/'build.log').read_text():raise RuntimeError('Vendor synthesis failed')
 if not (target/'impl/gwsynthesis/spectrum_bars.vg').exists():raise RuntimeError('Missing synthesized netlist')
 record['status']='passed_synthesis_only'
except Exception as error:
 record.update(status='failed',error=str(error));raise
finally:
 for f in (target/'impl/gwsynthesis').glob('*.html'):shutil.copy2(f,out/f.name)
 for name in ('build.tcl','build.log','spectrum_bars.v'):shutil.copy2(target/name,out/name)
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
