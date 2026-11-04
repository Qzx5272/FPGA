"""Explore latest combined exported netlist timing; NEVER PROGRAM auto IO."""
from pathlib import Path
import sys,hashlib,json,shutil,subprocess,datetime,re
b=Path(__file__).resolve().parents[1];source=Path(sys.argv[1]).resolve()
vg=source/'impl/gwsynthesis/combined_workstation.vg';assert vg.is_file()
from check_gw138_ram_modes import check as check_ram_modes
check_ram_modes(vg)
from vocoder_gate import require_vocoder_gate
vocoder_gate=require_vocoder_gate(source)
from stage_pad_gate import require_stage_pad_gate
stage_pad_gate=require_stage_pad_gate(source)
# Exploration only: display reader assumed50MHz, microphone BCK3.072MHz.
clocks={'core_clk':('clk',20.0),'mic_clk':('mic_bck',325.520833),'audio_clk':('audio_clk',40.690104),'display_clk':('display_clk',20.0)}
profile=json.loads((source/'hardware_profile.json').read_text())['hardware_profile'] if (source/'hardware_profile.json').exists() else 'workstation-i2s-spectrum-v1'
assert profile in ('workstation-i2s-spectrum-v1','workstation-i2s-rgb-v1')
if profile=='workstation-i2s-rgb-v1':clocks['display_clk']=('pixel_clk',39.682540)
sdc='# Internal exploratory clocks; NO actual external wiring/timing acceptance.\n'
for name,(port,period) in clocks.items():sdc+=f'create_clock -name {name} -period {period:.6f} [get_ports {{{port}}}]\n'
for a in clocks:
 for c in clocks:
  if a!=c:
   sdc+=f'set_max_delay -from [get_clocks {{{a}}}] -to [get_clocks {{{c}}}] 20.000\n'
   sdc+=f'set_min_delay -from [get_clocks {{{a}}}] -to [get_clocks {{{c}}}] 0.000\n'
targeted_hold='--cdc-hold' in sys.argv[2:]
if targeted_hold:
 # These are the21 negative hold endpoints observed in2d5bfcfe40c6:
 # first synchronizer stages, plus microphone payload published by Gray FIFO.
 # No synchronous hold relationship exists between these independent clocks.
 # Preserve all cross-domain20ns max-delay bounds and sync-stage2 checks.
 sdc+='''# Targeted asynchronous hold-only exceptions; never clock_groups/setup cuts.
set_false_path -hold -from [get_clocks {mic_clk}] -to [get_regs {band/input_audio/transport/fifo/wgray_r1* band/input_audio/latest* band/input_audio/held*}]
set_false_path -hold -from [get_clocks {audio_clk}] -to [get_regs {band/output_audio/fifo/rgray_w1* band/output_audio/request1* band/clock_watch/sync1*}]
set_false_path -hold -from [get_clocks {display_clk}] -to [get_regs {band/analyzer/display_frame/ack1*}]
'''
local_vocoder_control='--local-vocoder-control' in sys.argv[2:]
cst='IO_LOC "clk" P16;\nIO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=NONE;\n'
if local_vocoder_control:
 # SUG1018-1.7E section2.7: ordinary high-fanout control nets may use local
 # routing. These four exact nets consumed PRIMARY resources in35012423bf08.
 # This is a routing hypothesis, not a clock/timing exception or a netlist edit.
 for net in ('state_1_13','state_1_14','state_0_13','state_0_14'):
  cst+=f'CLOCK_LOC "band/engine/core/electronic_singer/audio/voice_core/bank/{net}" LOCAL_CLOCK;\n'
vg_hash=hashlib.sha256(vg.read_bytes()).hexdigest();digest=hashlib.sha256((vg_hash+sdc+'fourclock-bounded-v1'+(cst if local_vocoder_control else '')).encode()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('combined_workstation_pnr_'+digest)
if target.exists():raise RuntimeError('Do not overwrite existing build '+str(target))
target.mkdir();shutil.copytree(source/'rtl',target/'rtl')
(target/'hardware_profile.json').write_text(json.dumps({'hardware_profile':profile,'clocks':clocks},indent=2))
shutil.copytree(source/'impl/gwsynthesis',target/'impl/gwsynthesis')
for p in source.iterdir():
 if p.is_file() and p.suffix in ('.mem','.cst','.txt'):shutil.copy2(p,target/p.name)
(target/'stage.sdc').write_text(sdc)
(target/'stage.cst').write_text(cst)
tcl=(source/'build.tcl').read_text();assert tcl.count('run syn')==1
tcl=tcl.replace('foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}', 'add_file impl/gwsynthesis/combined_workstation.vg')
assert 'glob rtl' not in tcl
(target/'build.tcl').write_text(tcl.replace('run syn','add_file stage.sdc\nadd_file stage.cst\nrun pnr'))
(target/'NOT_PROGRAMMABLE.txt').write_text('NEVER PROGRAM:auto-placed peripheral IO. '+('Targeted hold-only CDC exceptions;' if targeted_hold else 'No false-path exceptions;')+' no physical CDC/MTBF or external timing acceptance.\n')
out=b/'evidence/combined_workstation_timing'/digest;out.mkdir(parents=True,exist_ok=False)
record=dict(status='running',build=str(target),source_build=str(source),frozen_netlist_sha256=vg_hash,hardware_profile=profile,requested_clocks=clocks,local_vocoder_control=local_vocoder_control,
 scope='Combined workstation exploratory PnR:four explicit clocks,20ns cross-domain maxdelay,zero mindelay,no false paths. No external pins,timing,CDC MTBF or physical acceptance.',
 started=datetime.datetime.now().isoformat(),inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (target/'build.tcl',target/'stage.sdc',target/'stage.cst',target/'hardware_profile.json',Path(__file__))})
if targeted_hold:
 record['scope']='Combined workstation exploratory PnR:four clocks,20ns cross-domain maxdelay;targeted hold-only exceptions on previously observed first-sync and microphone FIFO payload endpoints. No external pin/electrical/MTBF/physical acceptance.'
record['vocoder_numerical_gate']=vocoder_gate
record['stage_pad_numerical_gate']=stage_pad_gate
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(target,flush=True)
try:
 with (target/'build.log').open('w') as log:
  p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=3600)
 log=(target/'build.log').read_text(errors='replace');record['returncode']=p.returncode
 if p.returncode or 'ERROR' in log:raise RuntimeError('Vendor failure;inspect log')
 if hashlib.sha256((target/'impl/gwsynthesis/combined_workstation.vg').read_bytes()).hexdigest()!=vg_hash:raise RuntimeError('Frozen netlist changed')
 text=(target/'impl/pnr/combined_workstation_tr_content.html').read_text(encoding='utf-8',errors='replace')
 from check_stage_clock_report import check
 record['actual_clocks']=check(text,{n:v[1] for n,v in clocks.items()})
 for kind in ('Setup','Hold'):
  m=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',text)
  if not m:raise RuntimeError('Missing final timing summary')
  record[kind.lower()+'_violations']=int(m[1])
 record['status']='passed_internal_timing_only' if not(record['setup_violations'] or record['hold_violations']) else 'failed_timing'
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:
 for p in (target/'impl/pnr').glob('*'):
  if p.is_file() and p.suffix in ('.html','.txt','.timing_paths'):shutil.copy2(p,out/p.name)
 for name in ('build.tcl','stage.sdc','stage.cst','build.log','hardware_profile.json'):shutil.copy2(target/name,out/name)
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2));raise SystemExit(record['status']!='passed_internal_timing_only')
