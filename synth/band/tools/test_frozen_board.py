"""Run the existing board protocol regression against a frozen vendor-ROM candidate."""
from pathlib import Path
import sys,os,subprocess,hashlib,json,argparse
root=Path(__file__).resolve().parents[3];band=root/'synth/band'
ap=argparse.ArgumentParser();ap.add_argument('snapshot',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
snapshot=a.snapshot.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
original=(band/'tests/tb_board.v').read_text()
assert original.count('module tb_board;')==1
tb=out/'tb_board.v';tb.write_text(original.replace('module tb_board;',"module tb_board;\n GSR GSR(.GSRI(1'b1));"))
tools=root/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
sources=sorted(snapshot.glob('*.v'))
record=dict(status='running',scope='Frozen complete board RTL with vendor primitive model; no physical board or PnR claim',source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir() if p.is_file()},vendor_model_sha256=hashlib.sha256(vendor.read_bytes()).hexdigest(),test_sha256=hashlib.sha256(tb.read_bytes()).hexdigest())
report=out/'result.json';report.write_text(json.dumps(record,indent=2))
try:
    c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-I',str(snapshot),'-s','tb_board','-o',str(out/'test.vvp'),*[str(p) for p in sources],str(tb),str(vendor)],cwd=root,env=env,capture_output=True,text=True,timeout=60)
    (out/'compile.log').write_text(c.stdout+c.stderr)
    if c.returncode:raise RuntimeError('Compile failed')
    r=subprocess.run([str(tools/'vvp.exe'),str(out/'test.vvp')],cwd=root,env=env,capture_output=True,text=True,timeout=600)
    (out/'simulation.log').write_text(r.stdout+r.stderr)
    if r.returncode or 'PASS board top:' not in r.stdout:raise RuntimeError('Board regression failed')
    record.update(status='passed',log=r.stdout+r.stderr)
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:report.write_text(json.dumps(record,indent=2))
print(record['log'])
