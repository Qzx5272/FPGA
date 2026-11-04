"""Full experimental engine internal timing exploration. NEVER PROGRAM.

Microphone PCM and auxiliary I/O are automatically placed, without external
timing constraints. This proves only internal timing, never board pin safety.
"""
from pathlib import Path
import hashlib,json,shutil,subprocess,datetime,re
b=Path(__file__).resolve().parents[1];s=b/'experimental/vocoder'
files=list((b/'rtl').glob('*.v'))+list((b/'rtl').glob('*.vh'))+list((s/'ported').glob('*'))+list((s/'integration').glob('*'))+list((b/'experimental/audio_input').glob('*.v'))+[b.parent/'rtl'/n for n in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v')]
files=[p for p in files if p.is_file() and p.suffix in ('.v','.sv','.vh','.mem')]
assert len({p.name for p in files})==len(files),'Duplicate flattened source names'
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('singer_board_timing_'+digest)
if target.exists():raise RuntimeError('Inspect existing build: '+str(target))
(target/'rtl').mkdir(parents=True)
for p in files:shutil.copy2(p,target/('coeffs.mem' if p.suffix=='.mem' else 'rtl/'+p.name))
(target/'NEVER_PROGRAM.txt').write_text('AUTO-PLACED PCM/AUXILIARY IO. INTERNAL TIMING EXPLORATION ONLY. NOT A BOARD BITSTREAM.\n')
(target/'engine.sdc').write_text('create_clock -name core_clk -period 20.000 [get_ports {clk}]\n')
(target/'engine.cst').write_text('IO_LOC "clk" P16;\nIO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=NONE;\n')
(target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module band_singer_board_engine
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 0
foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}
add_file engine.sdc
add_file engine.cst
set_option -output_base_name singer_engine
run all
''')
e=b/'evidence/singer_board_timing';e.mkdir(exist_ok=True)
if (e/'result.json').exists():
 previous=json.loads((e/'result.json').read_text())
 history=e/'history'/Path(previous['build']).name
 if not history.exists():
  history.mkdir(parents=True)
  for old in e.iterdir():
   if old.is_file():shutil.copy2(old,history/old.name)
record=dict(status='running',scope='Full experimental engine internal50MHz timing; auto-placed other IO, no external delays; NEVER PROGRAM',sources=hashes,build=str(target),started=datetime.datetime.now().isoformat())
report=e/'result.json';report.write_text(json.dumps(record,indent=2))
try:
 with (target/'build.log').open('w') as f:
  p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=f,stderr=subprocess.STDOUT,timeout=5400)
 record['returncode']=p.returncode
 timing=target/'impl/pnr/singer_engine_tr_content.html'
 if p.returncode or not timing.exists():raise RuntimeError('Build failed; inspect captured log')
 text=timing.read_text(encoding='utf-8',errors='replace')
 for kind in ('Setup','Hold'):
  m=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',text)
  if not m:raise RuntimeError('Missing '+kind+' summary')
  record[kind.lower()+'_violations']=int(m[1])
 record['frequencies']=re.findall(r'\d+\.\d+\(MHz\)',text)[:2]
 record['status']='passed_internal_timing_only' if record['setup_violations']==record['hold_violations']==0 else 'failed_timing'
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:
 record['finished']=datetime.datetime.now().isoformat()
 for folder in ('gwsynthesis','pnr'):
  for p in (target/'impl'/folder).glob('*'):
   if p.is_file() and p.suffix in ('.html','.txt','.log','.timing_paths'):shutil.copy2(p,e/p.name)
 shutil.copy2(target/'build.log',e/'build.log');report.write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='sources'},indent=2))
