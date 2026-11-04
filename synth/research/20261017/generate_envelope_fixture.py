import random
from pathlib import Path
from envelope_reference import step,MAX
r=random.Random(13824);root=Path(__file__).resolve().parent/'deep'/'rtl'
cases=[(e,t,k,rem) for e in [0,1,MAX//2,MAX-1,MAX] for t in [0,MAX]
       for k in [0,1,54,322,805,1<<23,1<<24] for rem in [-(1<<23),0,1<<23]]
cases += [(r.randrange(MAX+1),r.randrange(MAX+1),r.randrange((1<<24)+1),r.randint(-(1<<23),1<<23)) for _ in range(30000)]
with (root/'envelope_vectors.txt').open('w') as f:
 for e,t,k,rem in cases:
  ne,nr=step(e,t,k,rem)
  if ne<0:ne,nr=0,0
  elif ne>MAX:ne,nr=MAX,0
  f.write(f'{e} {t} {k} {rem} {ne} {nr}\n')
print('vectors',len(cases))
