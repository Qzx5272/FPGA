"""Attribute synthesis resource deltas; primitive counts are NOT physical usage."""
from pathlib import Path
from collections import Counter
from functools import lru_cache
import sys,re,json,hashlib
b=Path(__file__).resolve().parents[1]
def analyze(path):
 raw=path.read_bytes();text=raw.decode()
 modules={name:Counter(re.findall(r'^\s+(\w+)\s+\S+\s*\(',body,re.M)) for name,body in re.findall(r'module\s+(\S+)\s*\((.*?)endmodule',text,re.S)}
 @lru_cache(None)
 def primitives(name):
  counts=Counter()
  for kind,n in modules[name].items():
   if kind in modules:
    for primitive,count in primitives(kind).items():counts[primitive]+=n*count
   else:counts[kind]+=n
  return counts
 result={}
 for name in modules:
  if name in ('offline_workstation_top','board_pt8211_dvi_top','board_pt8211_controls_top') or name.startswith(('stage_pad_frontend','double_biquad','vocoder_core')):
   counts=primitives(name)
   result[name]=dict(logic=sum(n for k,n in counts.items() if k.startswith('LUT') or k in ('ALU','INV')),
    ff=sum(n for k,n in counts.items() if k.startswith('DFF')),
    ram_primitives={k:n for k,n in counts.items() if k.startswith(('SDP','pROM','DPB','SPB'))},
    multiplier_primitives={k:n for k,n in counts.items() if k.startswith('MULT')})
 return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),modules=result)
before,after=[analyze(Path(p).resolve()) for p in sys.argv[1:3]]
record=dict(status='analysis_only',scope='Hierarchical synthesized primitive attribution;not physical usage,functional equivalence or timing proof',before=before,after=after)
digest=hashlib.sha256((before['sha256']+after['sha256']+hashlib.sha256(Path(__file__).read_bytes()).hexdigest()).encode()).hexdigest()[:12]
out=b/'evidence/synthesis_hierarchy';out.mkdir(exist_ok=True)
(out/(digest+'.json')).write_text(json.dumps(record,indent=2));print(out/(digest+'.json'))
for label,data in [('before',before),('after',after)]:
 print(label,{k:v for k,v in data['modules'].items() if k in ('offline_workstation_top','board_pt8211_dvi_top','board_pt8211_controls_top','vocoder_core','stage_pad_frontend')})
