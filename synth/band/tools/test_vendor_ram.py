from pathlib import Path
import subprocess,os,json,hashlib
root=Path(__file__).resolve().parents[3];os.chdir(root);band=root/'synth/band';binary=root/'tmp/oss-cad-suite/bin'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
sources=[band/'rtl/partial_ram16.v',band/'tests/tb_ram16_vendor.v',vendor];target=band/'evidence/vendor_ram.vvp'
c=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-DGOWIN_PRIMITIVES','-s','tb_ram16_vendor','-o',str(target),*[str(p) for p in sources]],env=env,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stdout+c.stderr)
r=subprocess.run([str(binary/'vvp.exe'),str(target)],env=env,capture_output=True,text=True,timeout=60)
record={'level':'Gowin primitive simulation','returncode':r.returncode,'output':r.stdout+r.stderr,'hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
(band/'evidence/vendor_ram.json').write_text(json.dumps(record,indent=2));print(r.stdout)
if r.returncode or 'PASS' not in r.stdout:raise RuntimeError(r.stderr+r.stdout)
