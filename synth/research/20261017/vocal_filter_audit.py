"""Illustrative vocal-section coefficients and static headroom audit, no voice model claim.

Formants below are engineering seed presets, not measured singers or a complete
Mandarin phoneme inventory. Normalization preserves each section's response shape.
"""
import json,math
from pathlib import Path
import numpy as np
FS=48000;Q=1<<21
PRESETS={'a':([750,1200,2600,3500,4500],[80,90,120,150,200]),
         'i':([280,2250,3000,3500,4500],[60,100,120,150,200]),
         'u':([350,800,2200,3300,4400],[60,80,120,150,200])}
z=np.exp(-2j*np.pi*np.arange(131073)/262144)

def denominator(f,bw):
 r=math.exp(-math.pi*bw/FS)
 return np.array([1.,-2*r*math.cos(2*math.pi*f/FS),r*r])

def audit(b,a,name):
 h=(b[0]+b[1]*z+b[2]*z*z)/(a[0]+a[1]*z+a[2]*z*z)
 gain=1/np.max(np.abs(h));b=b*gain
 aq=np.round(a*Q)/Q;bq=np.round(b*Q)/Q
 poles=np.roots(aq);hq=(bq[0]+bq[1]*z+bq[2]*z*z)/(aq[0]+aq[1]*z+aq[2]*z*z)
 impulse=np.fft.irfft(hq,n=262144)
 return {'name':name,'a':a.tolist(),'b_peak_normalized':b.tolist(),
         'a_q21':np.round(a*Q).astype(int).tolist(),'b_q21':np.round(b*Q).astype(int).tolist(),
         'quantized_peak_gain':float(np.max(abs(hq))),'quantized_impulse_l1':float(sum(abs(impulse))),
         'max_pole_radius':float(max(abs(poles))),
         'max_abs_coefficient':float(max(max(abs(aq)),max(abs(bq)))),
         'peak_frequency_hz':float(np.argmax(abs(hq))*FS/262144)}

def main():
 results=[]
 for vowel,(freq,bw) in PRESETS.items():
  for i,(f,w) in enumerate(zip(freq,bw)):
   results.append(audit(np.array([1.,0,0]),denominator(f,w),f'{vowel}_F{i+1}'))
 # Combined nasal pole/zero avoids individually huge inverse-DC gains.
 results.append(audit(denominator(700,100),denominator(250,80),'illustrative_nasal_pole_zero'))
 assert all(r['max_pole_radius']<1 and r['max_abs_coefficient']<4 for r in results)
 bounds={v:math.prod(r['quantized_impulse_l1'] for r in results if r['name'].startswith(v+'_')) for v in PRESETS}
 out={'scope':'static float/quantized coefficient response audit; not time-varying fixed-point singing or listening test',
      'sample_rate':FS,'coefficient_fraction_bits':21,'frequency_grid_points':131073,
      'preset_provenance':'engineering seed values, not copied phoneme corpus or measured singer',
      'sections':results,'conservative_five_section_l1_product':bounds,
      'required_actions':['apply source headroom using a proven bound or validated tighter transient bound',
                          'include nasal stage and noise branch in end-to-end headroom',
                          'check fixed-point recursive states and coefficient transitions separately',
                          'recover loudness through bounded output gain, not unchecked internal gain']}
 (Path(__file__).resolve().parent/'deep'/'vocal_filter_audit.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'sections':len(results),'all_static_stable':True,'cascade_l1_upper_bounds':bounds,
                   'maximum_section_l1':max(r['quantized_impulse_l1'] for r in results)},indent=2))
if __name__=='__main__':main()
