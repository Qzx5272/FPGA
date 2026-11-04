"""Synthesize the physically bounded onboard PT8211/DVI shell; never program."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('export',type=Path)
ap.add_argument('--onboard-controls',action='store_true',help='Experimental18-pin shell with S0/S1/S2; requires separate timing and pin audit')
args=ap.parse_args()
b=Path(__file__).resolve().parents[1];source=args.export.resolve()
manifest=json.loads((source/'export_manifest.json').read_text(encoding='utf-8'))
assert manifest['hardware_profile']=='workstation-pt8211-dvi-v1'
for n,h in manifest['sources'].items():assert hashlib.sha256((source/n).read_bytes()).hexdigest()==h,n
shell=b/'experimental/audio_visual/board_pt8211_dvi_top.sv'
if args.onboard_controls:shell=b/'experimental/audio_visual/onboard_controls/board_pt8211_controls_top.sv'
top=shell.stem
files=list((source/'rtl').iterdir())+list(source.glob('*.mem'))+[shell]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
pins=(source/'constraints/board.cst').read_text()+(b/'experimental/audio_visual/dvi/reference_HDMI0.cst.example').read_text()
if args.onboard_controls:pins+='\n'+(shell.parent/'buttons.cst').read_text()
digest=hashlib.sha256((json.dumps(hashes,sort_keys=True)+pins).encode()).hexdigest()[:12]
build=Path('D:/StarclusterBuilds')/('pt8211_onboard_syn_'+digest)
out=b/'evidence/pt8211_onboard_synthesis'/digest
if build.exists() or out.exists():raise RuntimeError('Preserve existing build: '+str(build))
shutil.copytree(source/'rtl',build/'rtl');out.mkdir(parents=True)
shutil.copy2(shell,build/'rtl'/shell.name);shutil.copy2(shell,out/shell.name)
for p in source.glob('*.mem'):shutil.copy2(p,build/p.name)
(build/'board.cst').write_text(pins)
tcl='''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module board_pt8211_dvi_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 1
foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}
set_option -output_base_name pt8211_onboard
run syn
'''
(build/'build.tcl').write_text(tcl.replace('set_option -top_module board_pt8211_dvi_top','set_option -top_module '+top))
(build/'NOT_PROGRAMMABLE.txt').write_text('Synthesis only; fixed pin template not yet PnR/IO/physical acceptance. No bitstream release.\n')
record=dict(status='running',build=str(build),export=str(source),sources=hashes,top_module=top,onboard_controls=args.onboard_controls,
 scope='Onboard PT8211+DVI shell synthesis only. UART supports host seats;mic/ADC/pedal unconnected and tiedoff. Full expansion source retained;not full-peripheral orphysical acceptance.',
 pin_template_sha256=hashlib.sha256((build/'board.cst').read_bytes()).hexdigest(),started=datetime.datetime.now().isoformat())
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(build,flush=True)
try:
 with (build/'build.log').open('w') as log:
  run=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(build/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=3600)
 logs=(build/'build.log').read_text(errors='replace')
 vg=build/'impl/gwsynthesis/pt8211_onboard.vg'
 if run.returncode or 'ERROR' in logs or not vg.is_file():raise RuntimeError('Vendor synthesis failed')
 record.update(status='passed_synthesis_only',netlist_sha256=hashlib.sha256(vg.read_bytes()).hexdigest())
except Exception as exc:
 record.update(status='failed_timeout' if isinstance(exc,subprocess.TimeoutExpired) else 'failed',error=str(exc));raise
finally:
 for p in (build/'impl/gwsynthesis').glob('*'):
  if p.is_file() and p.suffix in ('.html','.log','.xml'):shutil.copy2(p,out/p.name)
 for n in ('build.tcl','build.log','board.cst'):shutil.copy2(build/n,out/n)
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='sources'},indent=2))
