"""Synthesize the isolated vocoder chain; no pins, PnR, or programming."""
from pathlib import Path
import hashlib,json,shutil,subprocess,datetime
band=Path(__file__).resolve().parents[1]
sources=list((band/'rtl').glob('*.v'))+list((band/'rtl').glob('*.vh'))+list((band/'experimental/vocoder/ported').glob('*'))+list((band/'experimental/audio_input').glob('*.v'))+[band/'experimental/vocoder/integration/band_singer_core.sv']+[band.parent/'rtl'/n for n in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v')]
sources=[p for p in sources if p.is_file() and p.suffix in ('.v','.sv','.vh','.mem') and not p.name.startswith('tb_')]

hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('band_singer_core_syn_'+digest+'_flat')
if target.exists():raise RuntimeError('Inspect existing build rather than restarting: '+str(target))
(target/'rtl').mkdir(parents=True)
for p in sources:shutil.copy2(p,target/('coeffs.mem' if p.suffix=='.mem' else 'rtl/'+p.name))
(target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module band_singer_core
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 0
foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}
set_option -output_base_name band_singer_core
run syn
''')
out=band/'evidence/band_singer_core';out.mkdir(exist_ok=True)
record=dict(status='running',scope='Synthesis only; no physical timing/pin/integration acceptance',sources=hashes,build=str(target),started=datetime.datetime.now().isoformat())
path=out/'synthesis.json';path.write_text(json.dumps(record,indent=2))
try:
 with (target/'build.log').open('w') as f:r=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 record['returncode']=r.returncode
 reports=list((target/'impl/gwsynthesis').glob('*syn.rpt.html'))
 if r.returncode or 'ERROR' in (target/'build.log').read_text() or not reports:raise RuntimeError('Synthesis failed')
 for p in reports:shutil.copy2(p,out/p.name)
 shutil.copy2(target/'build.log',out/'synthesis.log')
 record.update(status='passed_synthesis_only',reports={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in reports})
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:path.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
