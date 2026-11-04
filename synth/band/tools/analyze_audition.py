"""Numerical audition checks; this does not claim perceptual/analog sound quality."""
import sys,json,wave,hashlib
from pathlib import Path
import numpy as np
p=Path(sys.argv[1]);report=p.with_suffix('.analysis.json')
with wave.open(str(p),'rb') as f:
 fs=f.getframerate();x=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').reshape(-1,2).astype(float)
assert fs==48000 and len(x)>=480000
names=['FM electric piano','held reed','vowel a','vowel e','vowel i','vowel o','vowel u','reed centered','reed bend up','reed bend down']
rows=[];spectra=[]
for i,name in enumerate(names):
 y=x[i*fs+4800:i*fs+24000,0];w=np.hanning(len(y));s=np.abs(np.fft.rfft(y*w));freq=np.fft.rfftfreq(len(y),1/fs)
 power=s*s;centroid=float(np.sum(freq*power)/max(np.sum(power),1))
 k=np.argmax(s[1:])+1
 delta=.5*(np.log(max(s[k-1],1e-9))-np.log(max(s[k+1],1e-9)))/(np.log(max(s[k-1],1e-9))-2*np.log(max(s[k],1e-9))+np.log(max(s[k+1],1e-9)))
 peak=(k+delta)*fs/len(y)
 rows.append(dict(name=name,rms=float(np.sqrt(np.mean(y*y))),peak_frequency_hz=float(peak),power_centroid_hz=centroid,tail_rms=float(np.sqrt(np.mean(x[i*fs+47000:(i+1)*fs,0]**2)))))
 spectra.append(s/np.linalg.norm(s))
vowel_distances=[float(1-np.dot(spectra[i],spectra[j])) for i in range(2,7) for j in range(i+1,7)]
bend_expected=[440,440*2**((127/64)/12),440*2**(-2/12)]
bend_errors=[abs(rows[7+i]['peak_frequency_hz']-f)/f for i,f in enumerate(bend_expected)]
checks={'all_segments_nonzero':all(r['rms']>10 for r in rows),'all_tails_decay':all(r['tail_rms']<r['rms']*.1 for r in rows),
 'different_vowel_spectra':min(vowel_distances)>.01,'bend_frequencies':max(bend_errors)<.005,'no_integer_clipping':not np.any(np.abs(x)>=32767)}
record=dict(status='passed' if all(checks.values()) else 'failed',evidence_level='RTL-generated digital waveform analysis, not listener or board acceptance',wav_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),checks=checks,segments=rows,minimum_vowel_cosine_distance=min(vowel_distances),maximum_bend_relative_error=max(bend_errors))
report.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
if record['status']!='passed':raise SystemExit(1)
