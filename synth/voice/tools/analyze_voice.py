"""Check actual RTL samples, and export an audition file (not a ROM asset)."""
import json,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
data=np.loadtxt(ROOT/'test-output/voice_samples.txt',dtype=np.int16)
assert len(data)==59600,len(data)
assert np.max(np.abs(data.astype(np.int32)))<32767
assert np.all(data[58200:58600]==0),'release not silent'
spectra=[]
for unit in range(7):
    segment=data[unit*7200+2400:(unit+1)*7200].astype(float)
    spectrum=np.abs(np.fft.rfft(segment*np.hanning(len(segment))))
    spectra.append(spectrum)
    assert np.sqrt(np.mean(segment**2))>20,unit
assert np.linalg.norm(spectra[0]-spectra[1])/np.linalg.norm(spectra[0])>.1
out=ROOT/'test-output/voice_vowels_rtl.wav'
with wave.open(str(out),'wb') as f:
    f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000);f.writeframes(data.tobytes())
report={'samples':len(data),'peak':int(np.max(np.abs(data.astype(np.int32)))),
        'release_silent':True,'vowel_spectra_differ':True,
        'intelligibility':'not verified by listener','source':'RTL simulation, not prerecorded synthesis input'}
(ROOT/'test-output/voice_analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
