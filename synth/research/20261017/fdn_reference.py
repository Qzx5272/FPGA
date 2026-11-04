"""Eight-delay fixed-point FDN impulse response, not a room realism test."""
import json,math
from pathlib import Path
import numpy as np
FS=48000;Q=1<<32;COEF=1<<21
LENGTHS=[1151,1277,1373,1481,1601,1723,1867,1999]

def rnd(z,b):return (z+(1<<(b-1)))>>b if z>=0 else -((-z+(1<<(b-1)))>>b)

def trial(t60,seconds=8):
 rings=[[0]*n for n in LENGTHS];pos=[0]*8
 gains=[int(math.floor(10**(-3*n/(FS*t60))*COEF)) for n in LENGTHS]
 output=np.empty(seconds*FS);peak_state=0;saturations=0
 for n in range(len(output)):
  taps=[rings[j][pos[j]] for j in range(8)]
  common=rnd(sum(taps),2)
  for j in range(8):
   value=rnd((taps[j]-common)*gains[j],21)+(Q//40 if n==0 else 0)
   peak_state=max(peak_state,abs(value))
   if not -(1<<35)<=value<(1<<35):saturations+=1
   rings[j][pos[j]]=max(-(1<<35),min((1<<35)-1,value));pos[j]=(pos[j]+1)%LENGTHS[j]
  output[n]=sum(v*(1 if i%2==0 else -1) for i,v in enumerate(taps))/(4*Q)
 energy=output*output;back=np.cumsum(energy[::-1])[::-1];back/=max(back[0],1e-100)
 db=10*np.log10(np.maximum(back,1e-300));mask=(db<=-5)&(db>=-35)
 fit=np.polyfit(np.arange(len(db))[mask]/FS,db[mask],1)
 tail=float(np.max(abs(output[-FS:])))
 return {'requested_t60_s':t60,'schroeder_t30_extrapolated_t60_s':float(-60/fit[0]),
         'state_peak_fs':peak_state/Q,'output_peak_fs':float(max(abs(output))),
         'last_second_peak_dbfs':20*math.log10(max(tail,1e-20)),
         'saturations':saturations,'gains_q21':gains}

results=[trial(t) for t in [.3,1,2,3]]
out={'scope':'fixed delay / fixed coefficient integer FDN; excludes lowpass damping, dynamic parameter changes, DAC and listening',
     'sample_rate':FS,'state_fraction_bits':32,'delay_lengths':LENGTHS,'results':results,
     'interpretation':'T30 estimates decay from -5 to -35 dB, not perceptual room similarity; finite-window tail results are not a proof for arbitrary switching'}
assert all(r['saturations']==0 for r in results)
(Path(__file__).resolve().parent/'deep'/'fdn_results.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
