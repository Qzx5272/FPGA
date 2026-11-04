"""Inventory locally produced engineering evidence. Run after final PDF build."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parent;DEEP=ROOT/'deep'
stress=json.loads((DEEP/'filter_stress_progress.json').read_text())
files=list(ROOT.glob('*.py'))+[ROOT/'V3_REPRODUCE.txt']
files+=list(DEEP.glob('*.json'))+list((DEEP/'rtl').glob('*.v'))+list((DEEP/'rtl').glob('*.sv'))
files+=list((DEEP/'rtl').glob('*.tcl'))+list((DEEP/'rtl').glob('*test.log'))
files+=list((DEEP/'rtl'/'impl/gwsynthesis').glob('*_research_syn.rpt.html'))
files+=[ROOT.parents[2]/'output/pdf/ORCHESTRA138_V3_FPGA_Engineering.pdf']
records=[]
for p in sorted(set(files)):
 if p.name=='evidence_manifest.json':continue
 data=p.read_bytes()
 records.append({'path':str(p.relative_to(ROOT.parents[2])).replace('\\','/'),
                 'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
out={'generated_utc':datetime.now(timezone.utc).isoformat(),'turn_started_utc':'2026-10-17T12:14:52+00:00',
     'long_experiment_status':stress['status'],'long_experiment_elapsed_seconds':stress['elapsed_seconds'],
     'scope':'research, standalone RTL simulation/synthesis and CPU reference models; no board programming or integrated audio certification',
     'files':records}
(DEEP/'evidence_manifest.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('Recorded',len(records),'files; stress status',stress['status'])
