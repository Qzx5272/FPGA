"""Check fixed Pro Dock HDMI0 routing and generated clocks on the small DVI boundary."""
from pathlib import Path
import sys,json,hashlib,shutil,subprocess,datetime,re
b=Path(__file__).resolve().parents[1];source=Path(sys.argv[1]).resolve()
vg=source/'impl/gwsynthesis/gowin_dvi_output.vg';assert vg.is_file()
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.v')}
proof=None
for p in sorted((b/'evidence/workstation_dvi').glob('*/result.json'),reverse=True):
 d=json.loads(p.read_text())
 if d.get('status')=='passed' and all(d.get('sources',{}).get(n)==h for n,h in hashes.items()):proof=p;break
if proof is None:
 # Small boundary exploration may use its dedicated PLL/serializer oracle.
 # The composition wrapper must still match a passed full-chain snapshot.
 wrapper='gowin_dvi_output.v'
 wrapper_proofs=[p for p in (b/'evidence/workstation_dvi').glob('*/result.json') if (lambda d:d.get('status')=='passed' and d.get('sources',{}).get(wrapper)==hashes[wrapper])(json.loads(p.read_text()))]
 for p in sorted((b/'evidence/gowin_dvi_clocked').glob('*/result.json'),reverse=True):
  d=json.loads(p.read_text())
  if wrapper_proofs and d.get('status')=='passed' and sum(x['matched_bits_per_lane'] for x in d.get('segments',[]))>=11000 and all(d.get('sources',{}).get(n)==h for n,h in hashes.items() if n!=wrapper):
   proof=p;break
assert proof,'Need source-matched PLL/serializer proof and validated composition wrapper' 
sdc='''create_clock -name reference_clk -period 20.000 [get_ports {clk50}]
create_generated_clock -name serial_clk -source [get_ports {clk50}] -multiply_by 63 -divide_by 25 [get_pins {video_clocks/pll/CLKOUT0}]
create_generated_clock -name pixel_clk -source [get_pins {video_clocks/pll/CLKOUT0}] -divide_by 5 [get_pins {video_clocks/divider/CLKOUT}]
'''
# SUG940-2.0.4E5.4.1: only asynchronous CLEAR pins of the two-stage
# reset bridge. D/Q paths and OSER reset recovery/removal remain timed.
sdc+='set_false_path -from [get_clocks {pixel_clk}] -to [get_pins {transmitter/serial_release_0_s0/CLEAR transmitter/serial_release_1_s0/CLEAR}]\n'
cst='IO_LOC "clk50" P16;\nIO_PORT "clk50" IO_TYPE=LVCMOS33 PULL_MODE=NONE;\nIO_LOC "resetn" G16;\nIO_PORT "resetn" IO_TYPE=LVCMOS33 PULL_MODE=NONE;\n'
for port,pair in {'tmds_d_p[0]':'AB24,AC24','tmds_d_p[1]':'V24,W24','tmds_d_p[2]':'AA22,AA23','tmds_clk_p':'Y22,Y23'}.items():
 cst+=f'IO_LOC "{port}" {pair};\nIO_PORT "{port}" IO_TYPE=LVCMOS33D PULL_MODE=NONE DRIVE=8;\n'
vg_hash=hashlib.sha256(vg.read_bytes()).hexdigest();digest=hashlib.sha256((vg_hash+sdc+cst).encode()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('dvi_output_pnr_'+digest);target.mkdir(exist_ok=False)
shutil.copytree(source/'impl/gwsynthesis',target/'impl/gwsynthesis')
(target/'display.sdc').write_text(sdc);(target/'display.cst').write_text(cst)
(target/'NOT_PROGRAMMABLE.txt').write_text('NEVER PROGRAM:only clock/reset/HDMI0 pins fixed;RGB inputs and diagnostic outputs automatic. No external IO timing or physical acceptance.\n')
(target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module gowin_dvi_output
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -output_base_name gowin_dvi_output
add_file impl/gwsynthesis/gowin_dvi_output.vg
add_file display.cst
add_file display.sdc
run pnr
''')
out=b/'evidence/dvi_output_timing'/digest;out.mkdir(parents=True)
record=dict(status='running',build=str(target),source_build=str(source),frozen_netlist_sha256=vg_hash,source_matched_simulation=str(proof),simulation_report_sha256=hashlib.sha256(proof.read_bytes()).hexdigest(),scope='Small clocked DVI boundary,officialHDMI0 pins and3 explicit related clocks;exception only on2 asynchronous reset-synchronizer CLEAR pins,not data/output paths. No fullband,external RGB input timing,physical display/jitter or programming acceptance.',started=datetime.datetime.now().isoformat())
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(target,flush=True)
try:
 with (target/'build.log').open('w') as log:p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=600)
 record['returncode']=p.returncode
 assert p.returncode==0 and 'ERROR' not in (target/'build.log').read_text(),'Vendor failure'
 assert hashlib.sha256((target/'impl/gwsynthesis/gowin_dvi_output.vg').read_bytes()).hexdigest()==vg_hash
 text=(target/'impl/pnr/gowin_dvi_output_tr_content.html').read_text(encoding='utf-8')
 from check_stage_clock_report import check
 record['actual_clocks']=check(text,{'reference_clk':20.0,'serial_clk':1000/126,'pixel_clk':1000/25.2})
 for kind in ('Setup','Hold'):
  match=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',text);assert match
  record[kind.lower()+'_violations']=int(match[1])
 record['status']='passed_internal_timing_only' if not(record['setup_violations'] or record['hold_violations']) else 'failed_timing'
except Exception as error:record.update(status='failed',error=str(error));raise
finally:
 for p in (target/'impl/pnr').glob('*'):
  if p.is_file() and p.suffix in ('.html','.txt','.timing_paths'):shutil.copy2(p,out/p.name)
 for name in ('build.log','build.tcl','display.sdc','display.cst'):shutil.copy2(target/name,out/name)
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2));raise SystemExit(record['status']!='passed_internal_timing_only')
