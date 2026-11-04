"""Measure a completed RTL render; refuse partial or failed PCM evidence."""
from pathlib import Path
import sys,json,hashlib,wave,math,array
report=Path(sys.argv[1]).resolve()
data=json.loads(report.read_text())
if data.get('status')!='passed':raise SystemExit('Render is not complete/passed')
if 'wav' in data:
 wav=Path(data['wav'])
 with wave.open(str(wav),'rb') as w:
  if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(2,2,48000):raise SystemExit('Unexpected WAV format')
  pcm=w.readframes(w.getnframes())
 frames=round(data['seconds']*48000)
else:
 # Workstation renders are raw stereo s16le; never turn running PCM into a demo.
 pcm=report.with_suffix('.pcm').read_bytes();frames=data['loaded_frames']
if hashlib.sha256(pcm).hexdigest()!=data['pcm_sha256']:raise SystemExit('PCM hash mismatch')
x=array.array('h');x.frombytes(pcm)
if sys.byteorder!='little':x.byteswap()
if len(x)!=frames*2:raise SystemExit('Incomplete audio')
segments=[]
for start in range(0,len(x),96000):
 a=x[start:start+96000];channels=(a[0::2],a[1::2]);rms=[math.sqrt(sum(v*v for v in ch)/len(ch)) for ch in channels]
 segments.append(dict(start_seconds=start/96000,frames=len(a)//2,peak=max(map(abs,a)),
  rms_dbfs=[20*math.log10(v/32768) if v else None for v in rms],
  dc_mean=[sum(ch)/len(ch) for ch in channels],rail_samples=sum(v in (-32768,32767) for v in a),
  all_zero=not any(a)))
result=dict(scope='Digital PCM descriptive measurements; not perceptual or physical audio acceptance',
 source_report=str(report),source_scope=data.get('scope'),pcm_sha256=data['pcm_sha256'],frames=len(x)//2,
 peak=max(map(abs,x)),rail_samples=sum(s['rail_samples'] for s in segments),segments=segments,
 final_stereo_sample=list(x[-2:]),last_100ms_peak=max(map(abs,x[-9600:])),
 final_second_all_zero=not any(x[-96000:]))
dest=report.with_name(report.stem+'_audio_metrics.json');dest.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='segments'},indent=2))
