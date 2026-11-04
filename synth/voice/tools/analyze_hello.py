"""Validate the dynamic phrase from RTL, and save an audition artifact."""
import json,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
samples=np.loadtxt(ROOT/'test-output/hello_samples.txt',dtype=np.int16)[:64000]
assert len(samples)==64000
peak=int(np.max(np.abs(samples.astype(np.int32))))
assert 100<peak<32767
assert np.all(samples[62000:]==0)
def rms(a,b):
    x=samples[int(a*48):int(b*48)].astype(float)
    return float(np.sqrt(np.mean(x*x)))
assert rms(200,350)>100
assert rms(700,950)>100
assert rms(490,520)<rms(200,350)*.05
report=dict(peak=peak,ni_rms=rms(200,350),hao_rms=rms(700,950),gap_rms=rms(490,520),
            duration_seconds=1.28,clipped=False,completion_silent=True,
            intelligibility='Requires human listening; not asserted by this test')
(ROOT/'test-output/hello_analysis.json').write_text(json.dumps(report,indent=2)+'\n')
with wave.open(str(ROOT/'test-output/hello_rtl.wav'),'wb') as f:
    f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000);f.writeframes(samples.tobytes())
print(json.dumps(report))
