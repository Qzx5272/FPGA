"""Synthesize the actual exported combined workstation; no invented IO/timing."""
from pathlib import Path
import sys,json,hashlib,shutil,subprocess,datetime
b=Path(__file__).resolve().parents[1];source=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(b/'host'))
from rom_contract import check_vocoder_rom
check_vocoder_rom(source/'rtl/filterbank.sv')
manifest=json.loads((source/'export_manifest.json').read_text(encoding='utf-8'))
assert manifest['hardware_profile'] in ('workstation-i2s-spectrum-v1','workstation-i2s-rgb-v1','workstation-i2s-dvi-v1')
for name,h in manifest['sources'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==h,name
files=list((source/'rtl').glob('*'))+list(source.glob('*.mem'))
hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('combined_workstation_syn_'+digest)
if target.exists():raise RuntimeError('Inspect existing build, do not overwrite '+str(target))
shutil.copytree(source/'rtl',target/'rtl')
(target/'hardware_profile.json').write_text(json.dumps({'hardware_profile':manifest['hardware_profile']}))
for p in source.glob('*.mem'):shutil.copy2(p,target/p.name)
(target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module offline_workstation_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 1
foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}
set_option -output_base_name combined_workstation
run syn
''')
(target/'NOT_PROGRAMMABLE.txt').write_text('SYNTHESIS ONLY:no external clocks/pins/IO delays/timing or physical acceptance.\n')
out=b/'evidence/combined_workstation_synthesis'/digest;out.mkdir(parents=True,exist_ok=False)
record=dict(status='running',build=str(target),export=str(source),sources=hashes,scope='Actual exported I2S/watchdog/band/ADC/pedal/mic/singer/HannFFT/frozen-display top synthesis only;no timing or physical acceptance',started=datetime.datetime.now().isoformat())
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(target,flush=True)
try:
 with (target/'build.log').open('w') as log:p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=3600)
 reports=list((target/'impl/gwsynthesis').glob('*syn.rpt.html'));record['returncode']=p.returncode
 record['status']='passed_synthesis_only' if p.returncode==0 and reports else 'failed'
except Exception as e:record.update(status='failed',error=str(e));raise
finally:
 for p in (target/'impl/gwsynthesis').glob('*'):
  if p.is_file() and p.suffix in ('.html','.log','.xml'):shutil.copy2(p,out/p.name)
 for name in ('build.tcl','build.log'):shutil.copy2(target/name,out/name)
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='sources'},indent=2));raise SystemExit(record['status']!='passed_synthesis_only')
