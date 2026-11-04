"""Replay frozen netlist with targeted async hold exceptions; keep max-delay bounds.
SUG1220-2.0E3.3.13:run pnr. SUG940-2.0.4E5.4.1:-hold does not cut setup.
Never program auto-assigned peripheral IO from this experiment.
"""
from pathlib import Path
import sys,hashlib,json,shutil,subprocess,datetime,re
b=Path(__file__).resolve().parents[1];source=Path(sys.argv[1]).resolve()
vg=source/'impl/gwsynthesis/band_stage.vg';assert vg.is_file()
sdc=(source/'stage.sdc').read_text()
assert 'set_false_path' not in sdc and 'set_clock_groups' not in sdc
sdc+='''# Async FIFO protocol boundaries only:hold/removal have no synchronous phase relation.
# Keep20ns cross-domain max-delay constraints; do NOT cut setup or sync-stage2.
set_false_path -hold -from [get_clocks {mic_clk}] -to [get_regs {band/input_audio/transport/fifo/wgray_r1* band/input_audio/latest* band/input_audio/held*}]
set_false_path -hold -from [get_clocks {core_clk}] -to [get_regs {band/input_audio/transport/fifo/rgray_w1*}]
'''
vg_hash=hashlib.sha256(vg.read_bytes()).hexdigest();digest=hashlib.sha256((vg_hash+sdc+'auto-vg-extension-v3').encode()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('stage_cdc_hold_'+digest)
if target.exists():raise RuntimeError('Do not overwrite existing build '+str(target))
target.mkdir();shutil.copytree(source/'rtl',target/'rtl')
shutil.copytree(source/'impl/gwsynthesis',target/'impl/gwsynthesis')
for p in source.iterdir():
 if p.is_file() and p.suffix in ('.mem','.cst','.txt'):shutil.copy2(p,target/p.name)
(target/'stage.sdc').write_text(sdc)
tcl=(source/'build.tcl').read_text();assert tcl.count('run all')==1
tcl=tcl.replace('foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}', 'add_file impl/gwsynthesis/band_stage.vg')
assert 'glob rtl' not in tcl
(target/'build.tcl').write_text(tcl.replace('run all','run pnr'))
(target/'NOT_PROGRAMMABLE.txt').write_text('NEVER PROGRAM:auto-placed peripheral IO. Targeted asynchronous FIFO hold exceptions, no physical CDC/MTBF or external timing acceptance.\n')
out=b/'evidence/stage_cdc_timing'/digest;out.mkdir(parents=True,exist_ok=False)
record=dict(status='running',build=str(target),source_build=str(source),frozen_netlist_sha256=vg_hash,
 scope='Internal stage PnR replay only:targeted async FIFO hold exceptions;20ns cross-domain setup/max-delay retained. No external pins,timing,CDC MTBF or physical acceptance.',
 started=datetime.datetime.now().isoformat(),inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (target/'build.tcl',target/'stage.sdc',target/'stage.cst',Path(__file__))})
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(target,flush=True)
try:
 with (target/'build.log').open('w') as log:
  p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=3600)
 log=(target/'build.log').read_text(errors='replace');record['returncode']=p.returncode
 if p.returncode or 'ERROR' in log:raise RuntimeError('Vendor failure;inspect log')
 if hashlib.sha256((target/'impl/gwsynthesis/band_stage.vg').read_bytes()).hexdigest()!=vg_hash:raise RuntimeError('Frozen netlist changed')
 text=(target/'impl/pnr/band_stage_tr_content.html').read_text(encoding='utf-8',errors='replace')
 from check_stage_clock_report import check
 record['actual_clocks']=check(text,{'core_clk':20.0,'mic_clk':325.520833})
 for kind in ('Setup','Hold'):
  m=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',text)
  if not m:raise RuntimeError('Missing final timing summary')
  record[kind.lower()+'_violations']=int(m[1])
 record['status']='passed_internal_timing_only' if not(record['setup_violations'] or record['hold_violations']) else 'failed_timing'
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:
 for p in (target/'impl/pnr').glob('*'):
  if p.is_file() and p.suffix in ('.html','.txt','.timing_paths'):shutil.copy2(p,out/p.name)
 for name in ('build.tcl','stage.sdc','stage.cst','build.log'):shutil.copy2(target/name,out/name)
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2));raise SystemExit(record['status']!='passed_internal_timing_only')
