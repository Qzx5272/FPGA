"""Run changed native button shell and fixed engine without repeating endurance."""
from pathlib import Path
import ast,os,json,subprocess
band=Path(__file__).resolve().parents[1];root=band.parents[1]
build=Path('D:/StarclusterBuilds/workstation_v6_native_fixed');out=Path('D:/StarclusterBuilds/v6_native_regression');out.mkdir(exist_ok=True)
tree=ast.parse((band/'tools/test_onboard_controls.py').read_text())
tb=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='tb' for t in n.targets))
tb=tb.replace('if(np||ns||dut.workstation.band.engine.panic)', 'if(dut.workstation.band.engine.FEATURE_FLAGS!=32\'h8000007c)$fatal(1,"false native capabilities");\n if(np||ns||dut.workstation.band.engine.panic)')
(out/'tb.v').write_text(tb)
binary=root/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
files=[p for p in (build/'rtl').iterdir() if p.suffix in ('.v','.sv') and not p.name.startswith('tb_')]
commands=[[str(binary/'iverilog.exe'),'-g2012','-I',str(build/'rtl'),'-s','tb','-o',str(out/'sim.vvp'),*map(str,files),str(out/'tb.v'),str(vendor)],
 [str(binary/'vvp.exe'),str(out/'sim.vvp')]]
logs=[]
for cmd in commands:
 p=subprocess.run(cmd,cwd=build,env=env,capture_output=True,text=True,timeout=300);logs.append(p.stdout+p.stderr)
 if p.returncode:break
record=dict(status='passed' if p.returncode==0 and 'PASS actual board shell' in logs[-1] else 'failed',
 scope='Actual new native full board shell: debounce,stop/play/panic,no auto resume; idle ADC removed,capabilities checked. Not physical button actuation.',logs=logs)
(out/'result.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
if record['status']!='passed':raise SystemExit(1)
