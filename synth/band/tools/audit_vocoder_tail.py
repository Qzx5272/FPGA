"""Bounded numerical audit, not a proof for every possible input sequence."""
from pathlib import Path
import json,math,hashlib,datetime
from generate_vocoder_coeffs import signed
B=Path(__file__).resolve().parents[1];S=B/'experimental/vocoder/ported/coeffs.mem'
rows=[[signed(x) for x in l.split()] for l in S.read_text().splitlines()]
history=[[[[0]*4 for _ in range(2)] for _ in range(3)] for _ in range(16)]
overflows=0;peak_state=0;tail_output=0;tail_state=0;clips=0
def run(x,c,h):
 global overflows,peak_state
 for j in range(2):
  x1,x2,y1,y2=h[j];b0,b1,b2,a1,a2=c[j*5:j*5+5]
  y=0
  for term in (b0*x>>20,-(a1*y1>>20),b1*x1>>20,-(a2*y2>>20),b2*x2>>20):
   y+=term
   overflows+=int(y < -2**31 or y>=2**31)
   y=(y+2**31)%2**32-2**31
  peak_state=max(peak_state,abs(y));h[j]=[x,x1,y,y1];x=y
 return x
for n in range(52096):
 # Broadband alternating impulse, then a low-band excitation; one second silence.
 x=(8388607 if n%2 else -8388608) if n<64 else int(7000000*math.sin(2*math.pi*58*n/48000)) if n<4096 else 0
 total=0
 for i in range(16):
  m=run(x,rows[i],history[i][0]);e=run(min(abs(m),2147483647),rows[16],history[i][1]);c=run(x,rows[i],history[i][2])
  total+=c*max(e,0)
  if n>=51136:tail_state=max(tail_state,abs(m),abs(e),abs(c))
 y=total>>23;clips+=int(y>8388607 or y < -8388608)
 if n>=51136:tail_output=max(tail_output,abs(y))
result=dict(status='passed' if overflows==0 and tail_output<=16 else 'needs_review',
 scope='Integer-model bounded 4096 excitation +48000 silence; no hardware or universal stability proof',
 coefficient_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 arithmetic_wrap_events=overflows,peak_state=peak_state,output_clip_samples=clips,
 final_960_sample_output_peak=tail_output,final_960_sample_state_peak=tail_state,
 completed=datetime.datetime.now().isoformat())
out=B/'evidence/vocoder_tail';out.mkdir(parents=True,exist_ok=True)
(out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
