"""Summarize a live or completed randomized numerical experiment without hiding warnings."""
from pathlib import Path
import json,collections,math
root=Path(__file__).resolve().parent/'deep'
progress=json.loads((root/'filter_stress_progress.json').read_text())
groups=collections.Counter();worst=[];loaded=0
for line in (root/'filter_stress_anomalies.jsonl').read_text().splitlines():
 try:r=json.loads(line)
 except json.JSONDecodeError:continue # A live writer can leave the last line incomplete.
 if r['kind']=='dynamic_resonator' and r['tail_peak_fs']>1e-4:
  groups[(r['q'],r['transition_samples'])]+=1;loaded+=1;worst.append(r)
worst.sort(key=lambda r:r['tail_peak_fs'],reverse=True)
counts=[]
for q in [15,21]:
 for step in [1,16,240,960]:
  residue=2*[1,16,240,960].index(step)+(q==21)
  n=max(0,(progress['trials']-1-residue)//8+1)
  k=groups[(q,step)]
  counts.append({'coefficient_fraction_bits':q,'transition_samples':step,
                 'trials_at_checkpoint':n,'tail_warnings_in_flushed_log':k,
                 'warning_fraction_approx':k/n if n else 0})
out={'status':progress['status'],'checkpoint_utc':progress['updated_utc'],
     'scope':'log grouping; a live checkpoint and flushed log may differ slightly; final run is aligned',
     'warning_threshold_dbfs':-80,'flushed_warning_records':loaded,'groups':counts,'worst_cases':worst[:5],
     'interpretation':'q groups use independent random draws; no board, listening, or complete V3 validation claim'}
(root/'filter_stress_analysis.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k!='worst_cases'},indent=2))
