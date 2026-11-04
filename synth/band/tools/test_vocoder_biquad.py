"""Independent fixed-point vectors plus an upstream mutation check for VOXOS port."""
from pathlib import Path
import random,json,hashlib,os,subprocess
root=Path(__file__).resolve().parents[3];b=root/'synth/band';src=b/'experimental/vocoder';out=b/'evidence/vocoder_biquad';out.mkdir(parents=True,exist_ok=True)
def signed32(n):return (n+2**31)%2**32-2**31
def section(c,x,x1,x2,y1,y2):
    # The upstream arithmetic rounds each product separately, then wraps each
    # addition to32 bits. Match that contract, not a floating-point approximation.
    terms=[c[0]*x,-(c[3]*y1>>20),c[1]*x1,c[4]*y2,c[2]*x2]
    y=signed32(terms[0]>>20)
    y=signed32(y+terms[1]);y=signed32(y+(terms[2]>>20))
    y=signed32(y-(terms[3]>>20));return signed32(y+(terms[4]>>20))
rng=random.Random(138);vectors=[]
for i in range(256):
    coeff=[rng.randint(-2097152,2097152) for _ in range(10)]
    values=[rng.randint(-8388608,8388607) for _ in range(7)]
    intermediate=section(coeff[:5],*values[:3],*values[3:5])
    final=section(coeff[5:],intermediate,*values[3:5],*values[5:7])
    vectors.extend(coeff+values+[intermediate,final])
(out/'vectors.hex').write_text('\n'.join(f'{n&0xffffffff:08x}' for n in vectors)+'\n')
names=['b0_0','b1_0','b2_0','a1_0','a2_0','b0_1','b1_1','b2_1','a1_1','a2_1','x_n','x_n1','x_n2','i_n1','i_n2','y_n1','y_n2']
tb='''`timescale 1ns/1ps
module tb_biquad;
 reg clk_in=0;always #10 clk_in=~clk_in;
 reg rst_in=1,valid_in=0;
 reg signed [31:0] '''+','.join(names)+''';
 wire signed [31:0] i_n,y_n;wire valid_out;
 double_biquad dut(.*);
 reg [31:0] vectors[0:4863];integer k,cycles,maximum=0;
 initial begin
  $readmemh("vectors.hex",vectors);
  repeat(4)@(negedge clk_in);rst_in=0;
  for(k=0;k<256;k=k+1)begin
'''+''.join(f'   {n}=vectors[k*19+{i}];\n' for i,n in enumerate(names))+'''
   valid_in=1;@(negedge clk_in);valid_in=0;cycles=0;
   while(!valid_out)begin @(negedge clk_in);cycles=cycles+1;if(cycles>100)$fatal(1,"deadline");end
   if(i_n!==vectors[k*19+17]||y_n!==vectors[k*19+18])$fatal(1,"fixed-point vector %0d got %h/%h expected %h/%h",k,i_n,y_n,vectors[k*19+17],vectors[k*19+18]);
   if(cycles>maximum)maximum=cycles;
   @(negedge clk_in);
  end
  // Reset must initialize both result registers even if no new input arrives.
  rst_in=1;@(negedge clk_in);
  if(i_n!==0||y_n!==0||valid_out!==0)$fatal(1,"reset output");
  $display("PASS256 independent signed fixed-point vectors, maxcycles=%0d, reset outputs",maximum);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
'''
(out/'tb_biquad.sv').write_text(tb)
tools=root/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
record=dict(status='running',scope='Double-biquad arithmetic/reset only; not full vocoder stability, audio quality or timing',results={},test_sha256=hashlib.sha256(tb.encode()).hexdigest(),vectors_sha256=hashlib.sha256((out/'vectors.hex').read_bytes()).hexdigest())
for variant in ('upstream','ported'):
    module=src/variant/'double_biquad.sv'
    c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-s','tb_biquad','-o',str(out/(variant+'.vvp')),str(module),str(out/'tb_biquad.sv')],env=env,capture_output=True,text=True)
    if c.returncode:raise RuntimeError(c.stderr)
    r=subprocess.run([str(tools/'vvp.exe'),str(out/(variant+'.vvp'))],cwd=out,env=env,capture_output=True,text=True,timeout=30)
    record['results'][variant]=dict(returncode=r.returncode,log=r.stdout+r.stderr,source_sha256=hashlib.sha256(module.read_bytes()).hexdigest())
record['status']='passed' if record['results']['ported']['returncode']==0 and record['results']['upstream']['returncode']!=0 and 'fixed-point vector' in record['results']['upstream']['log'] else 'failed'
(out/'result.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
if record['status']!='passed':raise SystemExit(1)
