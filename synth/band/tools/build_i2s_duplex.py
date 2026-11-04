"""Build isolated INMP441/PCM5102 bring-up image. Never programs SRAM/Flash."""
from pathlib import Path
import hashlib,json,shutil,subprocess,datetime,re
root=Path(__file__).resolve().parents[3]
src=root/'synth/band/experimental/i2s_duplex'
files=[src/n for n in ('audio_bringup_top.sv','i2s_master_duplex.sv','gowin_audio_clock.v','tone_1k.mem','board.cst','board.sdc')]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
out=Path('D:/StarclusterBuilds')/('i2s_duplex_'+digest)
out.mkdir(exist_ok=False)
for p in files:shutil.copy2(p,out/p.name)
tcl='''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module audio_bringup_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 1
add_file audio_bringup_top.sv
add_file i2s_master_duplex.sv
add_file gowin_audio_clock.v
add_file board.cst
add_file board.sdc
set_option -cst_warn_to_error 1
set_option -output_base_name i2s_duplex
run syn
run pnr
'''
(out/'build.tcl').write_text(tcl)
record={'status':'running','sources':hashes,'build':str(out),'started':datetime.datetime.now().isoformat(),
        'programmed':False,'scope':'isolated audio bring-up, not full workstation; physical audio pending'}
report=out/'result.json';report.write_text(json.dumps(record,indent=2))
print(out,flush=True)
try:
 with (out/'build.log').open('w') as log:
  p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(out/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
 text=(out/'build.log').read_text(errors='replace')
 if p.returncode or 'ERROR' in text:raise RuntimeError('Vendor failure, inspect build.log')
 timing=(out/'impl/pnr/i2s_duplex_tr_content.html').read_text(encoding='utf-8')
 for kind in ('Setup','Hold'):
  match=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',timing)
  if not match:raise RuntimeError('Missing timing summary')
  record[kind.lower()+'_violations']=int(match[1])
 from timing_pulse import pulse_rows
 rows=pulse_rows(timing)
 record['pulse_width_paths']=rows
 record['pulse_width_violations']=sum(p['slack_ns']<0 or p['actual_ns']<p['required_ns'] for p in rows)
 record['status']='routed_pending_pin_and_constraint_review' if not any(record[k+'_violations'] for k in ('setup','hold','pulse_width')) else 'timing_failed'
except Exception as e:
 record.update(status='failed',error=str(e));raise
finally:
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
