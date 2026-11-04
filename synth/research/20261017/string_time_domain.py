"""Rendered numerical impulse loops; test delay indexing against phase design.

No saved instrument audio, no perceptual pitch claim. Coefficients are quantized,
recurrence is float64 here so state-rounding coverage remains separate.
"""
import json,math
from pathlib import Path
import numpy as np
from string_calibration import design,FS

def render(p,seconds=8):
 ring=[0.0]*p['integer_delay'];ptr=0;prev_x=prev_l=prev_a=0.0
 s=p['loss_weight'];a=p['allpass_a'];g=p['gain']
 out=np.empty(round(seconds*FS))
 for i in range(len(out)):
  x=ring[ptr];lo=(1-s)*x+s*prev_x
  ap=a*lo+prev_l-a*prev_a
  prev_x=x;prev_l=lo;prev_a=ap
  ring[ptr]=g*ap+(1.0 if i==0 else 0.0)
  out[i]=x;ptr=(ptr+1)%len(ring)
 return out

def measured_peak(x,f):
 nfft=1<<21;window=np.hanning(len(x));spec=np.abs(np.fft.rfft(x*window,nfft))
 left=math.floor(f*.98*nfft/FS);right=math.ceil(f*1.02*nfft/FS)
 k=int(np.argmax(spec[left:right]))+left
 y=np.log(np.maximum(spec[k-1:k+2],1e-100));offset=.5*(y[0]-y[2])/(y[0]-2*y[1]+y[2])
 return (k+offset)*FS/nfft

rows=[]
for f in [27.5,55,82.4069,220,440,880,1760,3520]:
 for s in [.05,.5]:
  p=design(f,s,3);x=render(p);fq=measured_peak(x,f)
  rows.append({'f_hz':f,'loss_weight':s,'rendered_peak_hz':fq,
               'rendered_peak_error_cents':1200*math.log2(fq/f),
               'loop_phase_hz':p['frequency_from_loop_phase_hz'],
               'estimated_t60_s':p['estimated_effective_t60_s'],
               'gain_clamped':p['gain_clamped'],'peak_abs':float(max(abs(x)))})
out={'scope':'8-second float64 recurrences with quantized coefficients; FFT peak estimates, not state-quantized board audio',
     'cases':len(rows),'fft_length':1<<21,'window':'Hann, log-magnitude parabolic peak',
     'max_abs_rendered_peak_error_cents':max(abs(r['rendered_peak_error_cents']) for r in rows),'results':rows}
(Path(__file__).resolve().parent/'deep'/'string_time_domain_results.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k!='results'},indent=2))
