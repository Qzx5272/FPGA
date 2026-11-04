"""Run RTL tests with portable Icarus; only PASS text counts as successful."""
import os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
os.chdir(root)
out=root/'synth/test-output';out.mkdir(exist_ok=True)
bin_dir=root/'tmp/oss-cad-suite/bin'
env=os.environ.copy();env['PATH']=str(bin_dir)+os.pathsep+str(bin_dir.parent/'lib')+os.pathsep+env['PATH']
iverilog=str(bin_dir/'iverilog.exe'); vvp=str(bin_dir/'vvp.exe')
rtl=[str(p) for p in (root/'synth/rtl').glob('*.v')]
logs=[]
for tb in (sys.argv[1:] or ['uart','control','serial','engine','voice','hello','arranger']):
    target=str(out/(tb+'.vvp'))
    c=subprocess.run([iverilog,'-g2005','-I','synth/rtl','-s','tb_'+tb,'-o',target,*rtl,f'synth/tests/tb_{tb}.v'],capture_output=True,text=True,env=env)
    if c.returncode: print('Compiler failure',c.returncode,c.stdout,c.stderr);sys.exit(1)
    r=subprocess.run([vvp,target],capture_output=True,text=True,env=env,timeout=180)
    print(r.stdout.strip());logs.append(r.stdout+r.stderr)
    if r.returncode or 'FAIL' in r.stdout or 'PASS' not in r.stdout:sys.exit(1)
(out/'rtl_tests.log').write_text('\n'.join(logs),encoding='utf-8')
