"""Finite latest-source integration checks; no pins and no programming."""
from pathlib import Path
import os,subprocess,json
band=Path(__file__).resolve().parents[1];root=band.parents[1]
build=Path('D:/StarclusterBuilds/workstation_v6_expansion');binary=root/'tmp/oss-cad-suite/bin'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
files=[p for p in (build/'rtl').iterdir() if p.suffix in ('.v','.sv') and not p.name.startswith('tb_')]
results=[]
for top in ('tb_rom_song_loader_v6','tb_library_integration_v6','tb_instrument_v6','tb_expansion_v6'):
    exe=build/(top+'.vvp');tb=band/'tests'/(top+'.sv');logs=[]
    for cmd in ([str(binary/'iverilog.exe'),'-g2012','-I',str(build/'rtl'),'-s',top,'-o',str(exe),*map(str,files),str(tb)],
                [str(binary/'vvp.exe'),str(exe)]):
        p=subprocess.run(cmd,cwd=build,env=env,capture_output=True,text=True,timeout=300);logs.append(p.stdout+p.stderr)
        if p.returncode:break
    passed=p.returncode==0 and 'PASS' in logs[-1]
    (build/(top+'.log')).write_text('\n'.join(logs),encoding='utf-8')
    results.append(dict(test=top,passed=passed,log=logs[-1]));print(json.dumps(results[-1]),flush=True)
    if not passed:break
if all(r['passed'] for r in results):
    vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
    p=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-I',str(build/'rtl'),'-s','workstation_v6_complete_top','-s','GSR','-o',str(build/'complete_elaborated.vvp'),*map(str,files),str(vendor)],
                     cwd=build,env=env,capture_output=True,text=True,timeout=90)
    results.append(dict(test='complete_I2S_panel_FFT_DVI_elaboration',passed=p.returncode==0,log=p.stdout+p.stderr))
record=dict(status='passed' if all(r['passed'] for r in results) else 'failed',tests=results,
 scope='Source-only integration and bounded RTL. No expansion CST or physical hardware acceptance.')
(build/'latest_results.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(dict(status=record['status'],tests=len(results))))
if record['status']!='passed':raise SystemExit(1)
