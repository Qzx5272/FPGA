"""Synthesize the full external-peripheral top without inventing board pins.

Resource evidence only: no placement/routing, external timing certification or
programmable release is produced. The verified PT8211 release is untouched.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess
band=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--build-root',type=Path,default=Path('D:/StarclusterBuilds'))
ap.add_argument('--gowin',default='D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe');a=ap.parse_args()
sources=list((band/'rtl').glob('*'))+[band.parent/'rtl'/n for n in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v')]
sources=[p for p in sources if p.is_file()]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
target=a.build_root.resolve()/('workstation_syn_'+digest)
if target.exists():raise RuntimeError('Existing synthesis directory; inspect it instead of restarting: '+str(target))
snapshot=target/'rtl';snapshot.mkdir(parents=True)
for p in sources:shutil.copy2(p,snapshot/p.name)
tcl='''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module workstation_top
set_option -verilog_std v2001
set_option -use_cpu_as_gpio 1
foreach f [glob rtl/*.v] {add_file $f}
set_option -output_base_name workstation_synth
run syn
'''
(target/'build.tcl').write_text(tcl)
record=dict(status='running',started=datetime.datetime.now().isoformat(),source_sha256=hashes,
    build_directory=str(target),scope='Full local ADC/ownership/audio CDC/I2S synthesis; no assigned board pins or PnR')
evidence=band/'evidence/workstation_synthesis.json'
evidence.write_text(json.dumps(record,indent=2));print(target,flush=True)
try:
    with (target/'build.log').open('w') as f:
        r=subprocess.run([a.gowin,str(target/'build.tcl')],stdout=f,stderr=subprocess.STDOUT,timeout=10800)
    reports=list((target/'impl/gwsynthesis').glob('*syn.rpt.html'))
    log=(target/'build.log').read_text(errors='replace')
    if r.returncode or 'ERROR' in log or not reports:raise RuntimeError('Synthesis did not complete successfully; inspect build.log')
    destination=band/'evidence/workstation_synthesis';destination.mkdir(exist_ok=True)
    shutil.copy2(target/'build.log',destination/'build.log')
    for p in reports:shutil.copy2(p,destination/p.name)
    record.update(status='passed_synthesis_only',reports=[str(p) for p in reports],report_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in reports})
except Exception as e:
    record.update(status='failed',error=repr(e));raise
finally:
    record['finished']=datetime.datetime.now().isoformat();evidence.write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='source_sha256'},indent=2))
