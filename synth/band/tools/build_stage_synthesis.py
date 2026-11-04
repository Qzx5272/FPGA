"""Synthesize the complete stage top; no invented pins, PnR or bitstream."""
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,sys,re,argparse
ap=argparse.ArgumentParser();ap.add_argument('--timing',action='store_true');ap.add_argument('--physical-ports',action='store_true',help='Use the actual exported stage port boundary; no parallel diagnostic GPIO');ap.add_argument('--hierarchy',type=int,choices=(0,1),default=0);args=ap.parse_args()
b=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(b/'tools/prepare_stage_integration.py')],check=True)
folders=['rtl','experimental/vocoder/ported','experimental/vocoder/integration','experimental/audio_input','experimental/local_pedal','experimental/stage']
sources=[p for folder in folders for p in (b/folder).glob('*') if p.is_file() and p.suffix in ('.v','.sv','.vh','.mem') and not p.name.startswith('tb_')]
sources += [b.parent/'rtl'/n for n in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v')]
assert len({p.name for p in sources})==len(sources),'Duplicate flattened names'
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
digest=hashlib.sha256(json.dumps(dict(sources=hashes,physical_ports=args.physical_ports,hierarchy=args.hierarchy),sort_keys=True).encode()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/(('stage_timing_' if args.timing else 'stage_syn_')+digest)
if target.exists():raise RuntimeError('Inspect existing build, do not restart: '+str(target))
(target/'rtl').mkdir(parents=True)
for p in sources:shutil.copy2(p,target/('coeffs.mem' if p.suffix=='.mem' else 'rtl/'+p.name))
tcl='''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module band_stage_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 0
foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}
set_option -output_base_name band_stage
run syn
'''
if args.physical_ports:tcl=tcl.replace('set_option -top_module band_stage_top','set_option -top_module band_stage_physical_top')
tcl=tcl.replace('set_option -netlist_hierarchy 0',f'set_option -netlist_hierarchy {args.hierarchy}')
if args.timing:
 (target/'stage.sdc').write_text('''# Internal two-clock exploration; no external ADC/board timing acceptance.
# SUG940-2.0.4E sections3.8,5.2.5,5.4.2: clock_groups would override max_delay.
create_clock -name core_clk -period 20.000 [get_ports {clk}]
create_clock -name mic_clk -period 325.520833 [get_ports {mic_bck}]
set_max_delay -from [get_clocks {core_clk}] -to [get_clocks {mic_clk}] 20.000
set_max_delay -from [get_clocks {mic_clk}] -to [get_clocks {core_clk}] 20.000
set_min_delay -from [get_clocks {core_clk}] -to [get_clocks {mic_clk}] 0.000
set_min_delay -from [get_clocks {mic_clk}] -to [get_clocks {core_clk}] 0.000
''')
 (target/'stage.cst').write_text('IO_LOC "clk" P16;\nIO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=NONE;\n')
 tcl=tcl.replace('run syn','add_file stage.sdc\nadd_file stage.cst\nrun all')
(target/'build.tcl').write_text(tcl)
(target/'NOT_PROGRAMMABLE.txt').write_text('NEVER PROGRAM. Unassigned/auto-placed peripheral IO. No real external timing or electrical acceptance.\n')
out=b/'evidence'/('stage_timing' if args.timing else 'stage_synthesis');out.mkdir(exist_ok=True)
report=out/'result.json'
if report.exists():
 old=json.loads(report.read_text());history=out/'history'/Path(old['build']).name
 history.mkdir(parents=True,exist_ok=False)
 for p in out.iterdir():
  if p.is_file():shutil.copy2(p,history/p.name)
scope='Complete stage internal two-clock timing exploration,50MHz/3.072MHz with20ns cross-domain max delays; autoIO NEVERPROGRAM, no external timing/CDC MTBF or board acceptance' if args.timing else 'Complete stage synthesis only: ADC seats/pedal/microphone/singer/band/DAC; no timing or board acceptance'
record=dict(status='running',scope=scope,sources=hashes,build=str(target),started=datetime.datetime.now().isoformat())
record['top_module']='band_stage_physical_top' if args.physical_ports else 'band_stage_top'
record['netlist_hierarchy']=args.hierarchy
record['port_scope']='Actual exported physical interface, diagnostic parallel GPIO omitted' if args.physical_ports else 'Debug top exposes counters as parallel GPIO'
record['build_inputs']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.suffix in ('.tcl','.sdc','.cst')}
report.write_text(json.dumps(record,indent=2));print(target,flush=True)
try:
 with (target/'build.log').open('w') as log:
  p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=5400)
 record['returncode']=p.returncode
 reports=list((target/'impl/gwsynthesis').glob('*syn.rpt.html'))
 if p.returncode or 'ERROR' in (target/'build.log').read_text(errors='replace') or not reports:raise RuntimeError('Vendor build failed; inspect synthesis/PnR log for the failing phase')
 record.update(status='passed_synthesis_only',reports={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in reports})
 if args.timing:
  text=(target/'impl/pnr/band_stage_tr_content.html').read_text(encoding='utf-8',errors='replace')
  for kind in ('Setup','Hold'):
   match=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',text)
   if not match:raise RuntimeError('Missing '+kind+' timing summary')
   record[kind.lower()+'_violations']=int(match[1])
  record['status']='passed_internal_timing_only' if not(record['setup_violations'] or record['hold_violations']) else 'failed_timing'
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:
 for folder in ('gwsynthesis','pnr'):
  for p in (target/'impl'/folder).glob('*'):
   if p.is_file() and p.suffix in ('.html','.txt','.log','.timing_paths'):shutil.copy2(p,out/p.name)
 shutil.copy2(target/'build.log',out/'build.log')
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='sources'},indent=2))
if record['status']=='failed_timing':raise SystemExit(1)
