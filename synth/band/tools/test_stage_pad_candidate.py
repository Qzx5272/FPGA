"""Cycle-exact candidate comparison against the frozen pre-optimization pad RTL."""
from pathlib import Path
import os, subprocess, hashlib, json, sys, argparse
ap=argparse.ArgumentParser()
ap.add_argument('build',nargs='?')
ap.add_argument('--candidate',default='serial_dirty')
args=ap.parse_args()
assert Path(args.candidate).name==args.candidate
r=Path(__file__).resolve().parents[3]
b=r/'synth/band'
c=b/'experimental/stage/candidates'/args.candidate
files=[c/n for n in ('stage_pad_frontend.sv','reference.sv','tb.sv')]
vendor_files=[]
if args.build:
    build=Path(args.build).resolve()
    assert (build/'stage_pad_frontend.sv').read_bytes()==files[0].read_bytes()
    vendor_files=[build/'impl/gwsynthesis/stage_pad.vg',Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')]
digest=hashlib.sha256(b''.join(p.read_bytes() for p in files+vendor_files)).hexdigest()[:12]
out=b/'evidence/stage_pad_candidate'/digest
out.mkdir(parents=True,exist_ok=False)
binary=r/'tmp/oss-cad-suite/bin'
env=dict(os.environ)
env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
logs=[]
compile_files=files
if vendor_files:
    bench=out/'tb_vendor.sv'
    bench.write_text(files[2].read_text().replace('module tb;',"module tb;\n GSR GSR(.GSRI(1'b1));"))
    compile_files=[files[1],bench]+vendor_files
for cmd in ([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(out/'test.vvp'),*map(str,compile_files)],
            [str(binary/'vvp.exe'),str(out/'test.vvp')]):
    proc=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=600)
    logs.append(proc.stdout+proc.stderr)
    if proc.returncode:break
log=''.join(logs)
result=dict(status='passed' if proc.returncode==0 and 'PASS200000' in log else 'failed',
    scope='200000 cycle public-output equality against frozen calRAM reference with deterministic input, backpressure, reset and panic; no exhaustive equivalence, timing or hardware claim',
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},log=log)
if vendor_files:
    result['scope']='Vendor functional netlist versus frozen pre-optimization RTL, 200000 cycles; no timing or physical claim'
    result['vendor_inputs']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in vendor_files+[bench]}
    (out/'stage_pad.vg').write_bytes(vendor_files[0].read_bytes())
for p in files:(out/p.name).write_bytes(p.read_bytes())
(out/'result.json').write_text(json.dumps(result,indent=2))
print(log)
raise SystemExit(result['status']!='passed')
