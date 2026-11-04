"""Check active vendor constraints and bind the scope of an internal-only PnR."""
from pathlib import Path
import re,json,hashlib,html,sys
b=Path(__file__).resolve().parents[1]
build=Path(sys.argv[1]).resolve()
out=b/'evidence/combined_workstation_timing'/build.name.removeprefix('combined_workstation_pnr_')
report=build/'impl/pnr/combined_workstation_tr_content.html'
text=report.read_text(encoding='utf-8');sdc=build/'stage.sdc'
commands=[line.strip() for line in sdc.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
active=[]
for row in re.findall(r'<tr>(.*?)</tr>',text,re.S):
    cells=[html.unescape(re.sub('<[^>]*>','',v)).strip() for v in re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)]
    if len(cells)==3 and cells[1]=='Actived':active.append(cells[2])
result=json.loads((out/'result.json').read_text())
dvi=result.get('hardware_profile')=='workstation-i2s-dvi-v1'
reset_exception='set_false_path -from [get_clocks {display_clk}] -to [get_pins {video_output/transmitter/serial_release_0_s0/CLEAR video_output/transmitter/serial_release_1_s0/CLEAR}]'
reset_bridge=dvi and result.get('reset_bridge_exception') is not None
assert len(commands)==(33 if reset_bridge else 32 if dvi else 31) and all(c in active for c in commands)
expected=[('create_clock',3 if dvi else 4),('create_generated_clock',2 if dvi else 0),('set_max_delay',12),('set_min_delay',12),('set_false_path',4 if reset_bridge else 3)]
for prefix,count in expected:
    assert sum(c.startswith(prefix) for c in commands)==count
assert all(' -hold ' in c or (reset_bridge and c==reset_exception) for c in commands if c.startswith('set_false_path'))
if reset_bridge:assert commands.count(reset_exception)==1
assert not any('clock_groups' in c for c in commands)
assert result['status']=='passed_internal_timing_only'
assert hashlib.sha256((build/'impl/gwsynthesis/combined_workstation.vg').read_bytes()).hexdigest()==result['frozen_netlist_sha256']
resource=build/'impl/pnr/combined_workstation.rpt.txt';resource_text=resource.read_text()
resources={name:int(re.search(r'^\s*'+re.escape(label)+r'\s*\|\s*(\d+)/',resource_text,re.M)[1])
           for name,label in [('logic','Logic'),('ff','Register'),('cls','CLS'),('ram','BSRAM'),('dsp','DSP')]}
fmax=float(re.search(r'<td>core_clk</td>\s*<td>50\.000\(MHz\)</td>\s*<td>([\d.]+)\(MHz\)</td>',text)[1])
record=dict(status='passed_constraint_scope_only',scope=('33 SDC commands active;three base plus two generated clocks;2async CLEAR pin exception' if reset_bridge else '32 SDC commands active;three base plus two generated clocks' if dvi else '31 SDC commands active;four base clocks')+';12 bounded maxdelay,12mindelay,3hold-only exceptions. Not external IO/CDC MTBF/physical acceptance.',active_commands=commands,core_fmax_mhz=fmax,physical_resources=resources,
            sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (report,sdc,resource,Path(__file__))})
(out/'constraint_scope_check.json').write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k not in ('active_commands','sources')},indent=2))
