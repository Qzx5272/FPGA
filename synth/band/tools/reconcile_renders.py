"""Compare completed actual-RTL full/fast pairs without mistaking running JSON for failure."""
from pathlib import Path
import json,hashlib,datetime
band=Path(__file__).resolve().parents[1];rows=[]
for full in (band/'evidence').glob('band_*_full.json'):
 fast=full.with_name(full.name.replace('_full.json','_fast.json'))
 if not fast.exists():continue
 a=json.loads(full.read_text());b=json.loads(fast.read_text())
 if a.get('status')!='passed' or not a.get('pcm_sha256') or not b.get('pcm_sha256'):continue
 match=a['pcm_sha256']==b['pcm_sha256']
 rows.append(dict(full=full.name,fast=fast.name,match=match,full_pcm=a['pcm_sha256'],fast_pcm=b['pcm_sha256']))
 # Repair only the known earlier comparison bug, retaining an audit note.
 if b.get('status')=='failed' and b.get('returncode')==0 and match:
  b['prior_comparison_status']='failed before full-clock simulation had completed'
  b['status']='passed';b['comparison_reconciled_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 b['matches_full_clock_simulation']=match;fast.write_text(json.dumps(b,indent=2))
report=dict(evidence_level='PCM identity across completed full-clock and quiescent-skip RTL runs',pairs=rows)
(band/'evidence/full_fast_equivalence.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if any(not x['match'] for x in rows):raise SystemExit(1)
