"""Synthesize the isolated vocoder chain; no pins, PnR, or programming."""
from pathlib import Path
import hashlib,json,shutil,subprocess,datetime,sys
band=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(band/'host'))
from rom_contract import check_vocoder_rom
check_vocoder_rom(band/'experimental/vocoder/ported/filterbank.sv')
sources=[band/'experimental/vocoder/ported'/n for n in ('double_biquad.sv','filterbank.sv','vocoder_mixer.sv','vocoder_core.sv','coeffs.mem')]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('vocoder_core_syn_'+digest)
if target.exists():raise RuntimeError('Inspect existing build rather than restarting: '+str(target))
(target/'rtl').mkdir(parents=True)
for p in sources:shutil.copy2(p,target/('coeffs.mem' if p.suffix=='.mem' else 'rtl/'+p.name))
(target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module vocoder_core
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
foreach f [glob rtl/*.sv] {add_file $f}
set_option -output_base_name vocoder_core
run syn
''')
out=band/'evidence/vocoder_core';out.mkdir(exist_ok=True)
record=dict(status='running',scope='Synthesis only; no physical timing/pin/integration acceptance',sources=hashes,build=str(target),started=datetime.datetime.now().isoformat())
path=out/'synthesis.json';path.write_text(json.dumps(record,indent=2))
try:
 with (target/'build.log').open('w') as f:r=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=f,stderr=subprocess.STDOUT,timeout=600)
 reports=list((target/'impl/gwsynthesis').glob('*syn.rpt.html'))
 if r.returncode or 'ERROR' in (target/'build.log').read_text() or not reports:raise RuntimeError('Synthesis failed')
 for p in reports:shutil.copy2(p,out/p.name)
 shutil.copy2(target/'build.log',out/'synthesis.log')
 record.update(status='passed_synthesis_only',reports={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in reports})
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:path.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
