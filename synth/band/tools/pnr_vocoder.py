"""Isolated core PnR exploration. Auto-placed non-clock I/O: NEVER PROGRAM.

Only clk_in-to-clk_in timing is constrained. This is not board integration.
"""
from pathlib import Path
import json,hashlib,shutil,subprocess,re,datetime
B=Path(__file__).resolve().parents[1];E=B/'evidence/vocoder_core'
syn=json.loads((E/'synthesis.json').read_text(encoding='utf-8'))
assert syn['status']=='passed_synthesis_only'
source=Path(syn['build']);target=Path(str(source).replace('_syn_','_pnr_')+'_netlist')
from vocoder_gate import require_vocoder_gate
vocoder_gate=require_vocoder_gate(source)
if target.exists():raise RuntimeError('Inspect existing PnR rather than restarting: '+str(target))
target.mkdir()
shutil.copytree(source/'impl/gwsynthesis',target/'impl/gwsynthesis')
shutil.copytree(source/'rtl',target/'rtl');shutil.copy2(source/'coeffs.mem',target/'coeffs.mem')
for name,h in syn['sources'].items():
 p=target/('coeffs.mem' if name.endswith('.mem') else 'rtl/'+name)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==h
(target/'core.sdc').write_text('create_clock -name core_clk -period 20.000 [get_ports {clk_in}]\n')
(target/'core.cst').write_text('IO_LOC "clk_in" P16;\nIO_PORT "clk_in" IO_TYPE=LVCMOS33 PULL_MODE=NONE;\n')
tcl=(source/'build.tcl').read_text().replace('run syn','add_file core.sdc\nadd_file core.cst\nrun pnr')
tcl=tcl.replace('foreach f [glob rtl/*.sv] {add_file $f}','add_file impl/gwsynthesis/vocoder_core.vg')
assert 'glob rtl' not in tcl
(target/'build.tcl').write_text(tcl)
record=dict(status='running',scope='Standalone internal50MHz timing only; auto-placed other IO, no external delays, NEVER PROGRAM THIS BITSTREAM',sources=syn['sources'],build=str(target),started=datetime.datetime.now().isoformat())
record['vocoder_numerical_gate']=vocoder_gate
netlist=target/'impl/gwsynthesis/vocoder_core.vg'
record['frozen_netlist_sha256']=hashlib.sha256(netlist.read_bytes()).hexdigest()
path=E/'pnr.json';path.write_text(json.dumps(record,indent=2),encoding='utf-8')
try:
 with (target/'build.log').open('w') as log:
  r=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=3600)
 report=target/'impl/pnr/vocoder_core_tr_content.html'
 record['returncode']=r.returncode
 record['synthesis_reran']='GowinSynthesis finish' in (target/'build.log').read_text(errors='replace')
 if record['synthesis_reran'] or hashlib.sha256(netlist.read_bytes()).hexdigest()!=record['frozen_netlist_sha256']:raise RuntimeError('Frozen validated netlist changed or synthesis reran')
 if r.returncode or not report.exists():raise RuntimeError('PnR failed; inspect build.log')
 timing=report.read_text(encoding='utf-8',errors='replace')
 for kind in ('Setup','Hold'):
  m=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',timing)
  if not m:raise RuntimeError('Timing endpoint summary missing')
  record[kind.lower()+'_violations']=int(m[1])
 record['frequencies']=re.findall(r'\d+\.\d+\(MHz\)',timing)[:2]
 record['status']='passed_internal_timing_only' if record['setup_violations']==record['hold_violations']==0 else 'failed_timing'
 for suffix in ('rpt.txt','timing_paths','log','tr_content.html'):
  p=target/'impl/pnr'/('vocoder_core.'+suffix if suffix!='tr_content.html' else 'vocoder_core_tr_content.html')
  if p.exists():shutil.copy2(p,E/p.name)
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:
 shutil.copy2(target/'build.log',E/'pnr_build.log')
 path.write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
