"""Extend the original96s score with a pitch-following electronic singer role.

This creates composition/source assets, not a new full-song acceptance claim.
"""
from pathlib import Path
import sys,copy,json
b=Path(__file__).resolve().parents[1];sys.path.insert(0,str(b/'host'))
from score import load,validate,save
from offline import export_project
s=copy.deepcopy(load(b/'assets/confluence.json'));s['format']='starcluster-score-2';s['engine_profile']='singer-v1'
s['title']='星群·汇流·电子歌手版'
selected={e['serial'] for e in s['events'] if e['part']==6 and e['kind']==0 and 48*48000<=e['sample']<80*48000}
next_serial=max(e['serial'] for e in s['events'])+1;identities={old:next_serial+i for i,old in enumerate(sorted(selected))}
extra=[]
for e in s['events']:
 if e['part']==6 and e['kind'] in (0,1) and e['serial'] in selected:
  new=dict(e,part=15,serial=identities[e['serial']]);new['velocity']=min(90,e['velocity']);extra.append(new)
s['events']+=extra;s['events'].sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
s['performance']=dict(master=64,wet=24,tempo=120,root=0,collaboration=True,patches={'15':{'0':80}})
s['singer_arrangement']=dict(start_seconds=48,end_seconds=80,notes=len(selected),pitch_source='existing original lead melody',modulator='external live microphone; no prerecorded vocals',validation='score structure only; full96s singer audio/PnR/physical performance pending')
validate(s);save(b/'assets/confluence_singer.json',s)
target=b.parents[1]/'output/final_workstation_20261022/offline_singer_confluence'
export_project(s,target,autoplay=True)
print(json.dumps(dict(export=str(target),events=len(s['events']),singer_notes=len(selected),duration_seconds=s['duration_samples']/48000,scope=s['singer_arrangement']['validation']),indent=2))
