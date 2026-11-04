"""Isolated four-engine scheduler candidate; never changes selected board sources."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, os, datetime, argparse

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--flat-coefficients',action='store_true')
args=parser.parse_args()

band=Path(__file__).resolve().parents[1];root=band.parents[1]
release=band/'release/pt8211_dvi_062a944dcce1'
manifest=json.loads((release/'manifest.json').read_text())
base=release/'source_snapshot'
for name in ('filterbank.sv','double_biquad.sv','coeffs.mem'):
    assert hashlib.sha256((base/name).read_bytes()).hexdigest()==manifest['snapshot_sha256'][name]
text=(base/'filterbank.sv').read_text()
old=text[text.index('  generate\n'):text.index('  endgenerate')+len('  endgenerate')]
ports=[]
for port,expr in re.findall(r'\.(\w+)\(([^\n]+)\)',old):
    if port=='valid_in':expr='engine_launch'
    elif port=='valid_out':expr='engine_done[lane]'
    elif port=='i_n':expr='engine_i[lane]'
    elif port=='y_n':expr='engine_y[lane]'
    else:expr=expr.replace('[i]', '[group_index*4+lane]')
    if port!='COEFF_WIDTH':ports.append(f'.{port}({expr})')
assert len(ports)==23,len(ports)
block='''  // Experimental: four arithmetic engines retain all sixteen band histories.
  localparam GROUPS=N_FILTERS/4;
  reg [31:0] group_index;
  reg engine_launch,engine_busy;
  wire [3:0] engine_done;
  wire signed [31:0] engine_i[0:3],engine_y[0:3];
  initial begin if(N_FILTERS!=16)$fatal(1,"four-engine candidate requires16 bands");end
  generate for(genvar lane=0;lane<4;lane=lane+1)begin:shared_engines
    double_biquad #(.COEFF_WIDTH(COEFF_WIDTH)) bq(
      '''+',\n      '.join(ports)+''');
  end endgenerate
  always_ff @(posedge clk_in)begin
    if(rst_in)begin
      group_index<=0;engine_launch<=0;engine_busy<=0;filters_valid_out<=0;
      for(integer k=0;k<N_FILTERS;k=k+1)begin i_n[k]<=0;y_n[k]<=0;end
    end else begin
      engine_launch<=0;filters_valid_out<=0;
      if(filters_valid_in&&!engine_busy)begin
        group_index<=0;engine_launch<=1;engine_busy<=1;
      end else if(engine_busy&&(&engine_done))begin
        for(integer k=0;k<4;k=k+1)begin
          i_n[group_index*4+k]<=engine_i[k];y_n[group_index*4+k]<=engine_y[k];
        end
        if(group_index==GROUPS-1)begin
          filters_valid_out<={N_FILTERS{1'b1}};engine_busy<=0;
        end else begin group_index<=group_index+1;engine_launch<=1;end
      end
    end
  end
'''
candidate=text.replace(old,block)
if args.flat_coefficients:
    candidate=candidate.replace('coeffs [N_FILTERS-1:0] [9:0]', 'coeffs [0:N_FILTERS*10-1]')
    candidate,count=re.subn(r'coeffs\[([^\]]+)\]\[([^\]]+)\]', r'coeffs[(\1)*10+(\2)]',candidate)
    assert count==14,count
digest=hashlib.sha256(candidate.encode()).hexdigest()[:12]
out=band/'experimental/vocoder/four_engines'/digest;out.mkdir(parents=True,exist_ok=True)
assert not (out/'filterbank.sv').exists(),'Preserve prior candidate'
(out/'filterbank.sv').write_text(candidate)
for name in ('double_biquad.sv','coeffs.mem'):shutil.copy2(base/name,out/name)
evidence=band/'evidence/filterbank_four_engines'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');evidence.mkdir(parents=True)
reference=band/'evidence/vocoder_filterbank'
tb=(reference/'tb.sv').read_text().replace('if(cycles>200)', 'if(cycles>1000)')
tb=re.sub(r'\.COEFF_FILE\("[^"]+"\)', '.COEFF_FILE("'+(out/'coeffs.mem').as_posix()+'")',tb)
(evidence/'tb.sv').write_text(tb);shutil.copy2(reference/'vectors.hex',evidence/'vectors.hex')
cad=root/'tmp/oss-cad-suite';env=dict(os.environ);env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH']
files=[out/'filterbank.sv',out/'double_biquad.sv',out/'coeffs.mem',evidence/'tb.sv',evidence/'vectors.hex',Path(__file__)]
record=dict(status='running',candidate=str(out),scope='Isolated experimental16-band filterbank with4arithmetic engines,4096 independent-reference samples; no whole-core/timing/board/resource claim',source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
report=evidence/'result.json';report.write_text(json.dumps(record,indent=2));print(str(report),flush=True)
shutil.copy2(Path(__file__),evidence/'generator_snapshot.py')
c=subprocess.run([str(cad/'bin/iverilog.exe'),'-g2012','-s','tb','-o',str(evidence/'sim.vvp'),str(out/'double_biquad.sv'),str(out/'filterbank.sv'),str(evidence/'tb.sv')],env=env,capture_output=True,text=True)
(evidence/'compile.log').write_text(c.stdout+c.stderr)
if c.returncode:
    record.update(status='failed_compile',log=c.stdout+c.stderr)
else:
    run=subprocess.run([str(cad/'bin/vvp.exe'),str(evidence/'sim.vvp')],cwd=evidence,env=env,capture_output=True,text=True,timeout=180)
    record.update(status='passed' if run.returncode==0 and 'PASS4096' in run.stdout else 'failed',log=run.stdout+run.stderr)
report.write_text(json.dumps(record,indent=2));print(record['status'],record['log'])
raise SystemExit(0 if record['status']=='passed' else 1)
