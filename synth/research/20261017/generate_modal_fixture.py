from pathlib import Path
import random,math,json
root=Path(__file__).resolve().parent/'deep'/'rtl';r=random.Random(13832)
def rounded(z):return (z+2**20)//2**21 if z>=0 else -((-z+2**20)//2**21)
limit=2**35
rows=[]
for i in range(20000):
    # Stable rotations plus deliberate overloads for saturation-path coverage.
    f=r.uniform(50,20000);bw=r.uniform(5,3000);rad=math.exp(-math.pi*bw/48000)
    a=round(2**21*rad*math.cos(2*math.pi*f/48000));b=round(2**21*rad*math.sin(2*math.pi*f/48000))
    x=r.randrange(-limit,limit);y=r.randrange(-limit,limit);d=r.randrange(-limit//8,limit//8)
    nx=rounded(a*x-b*y+(d<<21));ny=rounded(b*x+a*y);sat=int(not(-limit<=nx<limit and -limit<=ny<limit))
    nx=max(-limit,min(limit-1,nx));ny=max(-limit,min(limit-1,ny))
    rows.append((x,y,d,a,b,nx,ny,sat))
(root/'modal_vectors.txt').write_text('\n'.join(' '.join(map(str,row)) for row in rows)+'\n')
print('Generated',len(rows),'state transitions, including overload cases; seed 13832')
