"""Bounded full-clock render of actual board engine candidate. No hashes/repetition."""
from pathlib import Path
import os,subprocess,shutil,json,time,wave
band=Path(__file__).resolve().parents[1];root=band.parents[1];candidate=Path('D:/StarclusterBuilds/workstation_v6_20261027')
build=Path('D:/StarclusterBuilds/v6_engine_probe');build.mkdir(exist_ok=True)
out=Path('D:/StarclusterDeliveries/workstation_upgrade_20261027');cad=root/'tmp/oss-cad-suite';vr=cad/'share/verilator'
env=dict(os.environ);env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH'];env['VERILATOR_ROOT']=str(vr)
def run(cmd,log):
 with (build/log).open('w',encoding='utf-8') as f:p=subprocess.run(cmd,cwd=candidate,env=env,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(str(build/log))
files=list((candidate/'rtl').glob('*.v'))+list((candidate/'rtl').glob('*.sv'))+[band/'tests/v6_engine_probe.sv']
run([str(cad/'bin/verilator_bin.exe'),'--cc','--no-timing','--top-module','v6_engine_probe','--Mdir',str(build),'-Wno-fatal','-I'+str(candidate/'rtl'),*map(str,files)],'verilator.log')
exe=build/'render.exe'
run(['C:/mingw64/bin/g++.exe','-O3','-std=c++17','-pthread','-I'+str(build),'-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),
 str(band/'tests/v6_engine_probe.cpp'),*map(str,build.glob('*.cpp')),str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)],'compile.log')
env['PATH']='C:/mingw64/bin'+os.pathsep+env['PATH'];pcm=out/'v6_song_engine.pcm';start=time.monotonic()
p=subprocess.run([str(exe),str(pcm),str(12*48000)],cwd=candidate,env=env,capture_output=True,text=True,timeout=900)
record=dict(status='passed' if p.returncode==0 else 'failed',scope='Actual board engine12s, full50MHz clocks,PT8211 queue; no analog listening or DVI physical claim',
 elapsed_s=time.monotonic()-start,log=p.stdout+p.stderr,build_id=0x20261028)
(out/'v6_engine_result.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2),flush=True)
if p.returncode:raise RuntimeError('Engine render failed')
with wave.open(str(pcm.with_suffix('.wav')),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm.read_bytes())
