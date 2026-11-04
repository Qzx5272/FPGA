"""Render actual new HDL algorithms, with bounded full-clock probes and spectra."""
from pathlib import Path
import os,sys,subprocess,shutil,json,wave
import numpy as np
band=Path(__file__).resolve().parents[1];root=band.parents[1]
sys.path.insert(0,str(band/'host'))
from instruments import PRESETS,envelope
pool='--pool32' in sys.argv
build=Path('D:/StarclusterBuilds')/('v6_pool32_probe' if pool else 'v6_timbre_probe');build.mkdir(exist_ok=True)
out=Path('D:/StarclusterDeliveries/workstation_upgrade_20261027')/('pool32_auditions' if pool else 'timbre_auditions');out.mkdir(parents=True,exist_ok=True)
cad=root/'tmp/oss-cad-suite';vr=cad/'share/verilator';env=dict(os.environ)
env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+'C:/mingw64/bin'+os.pathsep+env['PATH'];env['VERILATOR_ROOT']=str(vr)
sources=[band/'tests/v6_timbre_probe.v',band/'experimental/shared_voices/shared_band_renderer.v',root/'synth/rtl/hq_sine_quarter.v']
if pool:
    text=sources[0].read_text(encoding='utf-8').replace('wire query,retire;', 'wire[4:0]query;wire retire;')
    text=text.replace('.VOICES(1),.INDEX_BITS(1)', '.VOICES(32),.INDEX_BITS(5)')
    text=text.replace("query,1'b1,gate,note,7'd100,part,32'd1,", "query,1'b1,gate,(note+{2'd0,query}),7'd100,part,(32'd1+query),")
    sources[0]=build/'pool_probe.v';sources[0].write_text(text,encoding='utf-8')
def run(cmd,log):
 with (build/log).open('w',encoding='utf-8') as f:p=subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(str(build/log))
run([str(cad/'bin/verilator_bin.exe'),'--cc','--top-module','v6_timbre_probe','--Mdir',str(build),'-Wno-fatal',
 '-I'+str(band/'rtl'),'-I'+str(root/'synth/rtl'),*map(str,sources)],'verilator.log')
exe=build/'render.exe'
run(['C:/mingw64/bin/g++.exe','-O3','-std=c++17','-pthread','-I'+str(build),'-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),
 str(band/'tests/v6_timbre_probe.cpp'),*map(str,build.glob('*.cpp')),str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)],'compile.log')
env['PATH']='C:/mingw64/bin'+os.pathsep+env['PATH']
results=[];all_audio=[]
for preset in PRESETS:
 if pool and preset['part'] not in (7,8,10,12):continue
 p=envelope(*preset['adsr']);pcm=out/(preset['id']+'.pcm')
 proc=subprocess.run([str(exe),str(pcm),str(preset['part']),'60',str(p[4]),str(p[5]),str(p[6]),str(p[7])],env=env,capture_output=True,text=True)
 if proc.returncode:raise RuntimeError(preset['id']+' '+proc.stdout+proc.stderr)
 samples=np.frombuffer(pcm.read_bytes(),dtype='<i2').reshape(-1,2)
 wpath=pcm.with_suffix('.wav')
 with wave.open(str(wpath),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(samples.tobytes())
 tone=samples[1000:10000,0].astype(float);spectrum=abs(np.fft.rfft(tone*np.hanning(len(tone))));freq=np.fft.rfftfreq(len(tone),1/48000)
 top=np.argsort(spectrum)[-6:][::-1]
 results.append(dict(id=preset['id'],part=preset['part'],name=preset['name'],log=proc.stdout.strip(),rms=float(np.sqrt(np.mean(tone**2))),
 peaks_hz=[round(float(freq[i]),2) for i in top],tail_peak=int(np.max(abs(samples[-500:,0].astype(int)))),wav=str(wpath)))
 all_audio.extend([samples,np.zeros((2400,2),dtype=np.int16)])
 print(preset['id']+': '+proc.stdout.strip(),flush=True)
with wave.open(str(out/'all_instruments.wav'),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(np.concatenate(all_audio).astype('<i2').tobytes())
(out/'results.json').write_text(json.dumps(dict(scope=('Actual HDL32 independent slots,consecutive MIDI60..91' if pool else 'Actual HDL single-voice algorithms')+',18k frames each,50MHz/48kHz; no DAC/listening claim',results=results),ensure_ascii=False,indent=2),encoding='utf-8')
