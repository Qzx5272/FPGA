"""Verify all FFT bins against floating mathematical reference, plus RTL stalls."""
from pathlib import Path
import os,sys,math,cmath,random,subprocess,json,hashlib,time
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/audio_visual'
n=int(sys.argv[1]) if len(sys.argv)>1 else 2048
if n not in (16,512,2048):raise ValueError('Supported fixtures:16,512,2048')
log_n=n.bit_length()-1;o=b/'evidence/fft_fixed'/str(n);o.mkdir(parents=True,exist_ok=True)
k1,k2=(3,5) if n==16 else (13,79)
rng=random.Random(138)
inputs=[
 [complex(round(12000*math.cos(2*math.pi*k1*i/n)+3000*math.sin(2*math.pi*k2*i/n)),0) for i in range(n)],
 [complex(round(10000*math.cos(2*math.pi*7*i/n)+700),round(10000*math.sin(2*math.pi*7*i/n)-350)) for i in range(n)],
 [complex(rng.randint(-3000,3000),rng.randint(-3000,3000)) for i in range(n)],
 [complex(-32768 if i==0 else 0,0) for i in range(n)],
 [0j]*n,
 [complex(32767 if math.cos(2*math.pi*k1*i/n)>=0 else -32767,32767 if math.sin(2*math.pi*k1*i/n)>=0 else -32767) for i in range(n)]]
fixture=o/'input.hex';fixture.write_text('\n'.join(f'{((int(x.real)&65535)<<16)|(int(x.imag)&65535):08x}' for frame in inputs for x in frame)+'\n')
tb='''`timescale 1ns/1ps
module tb;
localparam N=SIZE,LOG_N=LOG;
reg clk=0;always #5 clk=~clk;
reg rst=1,start=0,iv=0,orr=0;wire sr,ir,ov,done;
reg signed[15:0]xr=0,xi=0;wire signed[15:0]yr,yi;wire[LOG_N-1:0]bin;
wire[31:0]rejects,clips;reg[31:0]data[0:6*N-1];integer f,i,j,file,cycles=0,begin_compute=0,max_compute=0;reg signed[15:0]held_r,held_i;
fft_fixed #(.LOG_N(LOG_N),.TWIDDLE_FILE("TWIDDLE")) dut(clk,rst,start,sr,iv,ir,xr,xi,ov,orr,bin,yr,yi,done,rejects,clips);
always @(posedge clk)cycles=cycles+1;
initial begin
 $readmemh("INPUT",data);file=$fopen("OUTPUT","w");repeat(3)@(negedge clk);rst=0;#1;
 for(f=0;f<6;f=f+1)begin
  if(!sr)$fatal(1,"not ready for transform");start=1;@(negedge clk);start=0;
  for(i=0;i<N;i=i+1)begin
   if(!ir)$fatal(1,"lost input readiness");{xr,xi}=data[f*N+i];iv=1;start=i==3;@(negedge clk);iv=0;start=0;
   if(i%7==0&&i!=N-1)begin repeat(2)@(negedge clk);if(ov)$fatal(1,"partial input produced result");end
  end
  begin_compute=cycles;wait(ov);@(negedge clk);if(cycles-begin_compute>max_compute)max_compute=cycles-begin_compute;
  for(i=0;i<N;i=i+1)begin
   while(!ov)@(negedge clk);if(bin!=i)$fatal(1,"bin order");held_r=yr;held_i=yi;
   if(i%17==0)repeat(3)begin @(negedge clk);if(!ov||bin!=i||yr!==held_r||yi!==held_i)$fatal(1,"backpressure changed output");end
   $fwrite(file,"%0d %0d %0d %0d\\n",f,i,$signed(yr),$signed(yi));orr=1;@(negedge clk);orr=0;
  end
  if(!done||!sr||(f<5?clips!=0:clips==0)||rejects!=f+1)$fatal(1,"completion/counters clips=%0d rejects=%0d",clips,rejects);
 end
 start=1;@(negedge clk);start=0;iv=1;repeat(3)@(negedge clk);iv=0;rst=1;repeat(2)@(negedge clk);rst=0;
 repeat(4)@(negedge clk);if(ov||!sr||rejects||clips)$fatal(1,"reset did not discard partial load");
 $fclose(file);$display("PASS FFT N=%0d transforms=6 max_compute_clocks=%0d,stall/input gaps/busy start/reset",N,max_compute);$finish;
end
initial begin #1000000000;$fatal(1,"timeout");end
endmodule
'''.replace('SIZE',str(n)).replace('LOG;',str(log_n)+';').replace(chr(34)+'TWIDDLE'+chr(34),chr(34)+(s/f'fft_twiddle_{n}.mem').as_posix()+chr(34)).replace('INPUT',fixture.as_posix()).replace('OUTPUT',(o/'bins.txt').as_posix())
(o/'tb.v').write_text(tb)
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
sources=[s/'fft_fixed.v',s/f'fft_twiddle_{n}.mem',o/'tb.v',fixture,Path(__file__)]
record=dict(status='running',n=n,scope='Isolated FFT RTL numeric/handshake verification; no synthesis,timing or stage integration claim',sources={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
(o/'result.json').write_text(json.dumps(record,indent=2))
c=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(o/'test.vvp'),str(s/'fft_fixed.v'),str(o/'tb.v')],env=env,capture_output=True,text=True)
record['compile_log']=c.stdout+c.stderr
if c.returncode:record['status']='failed'
else:
 p=subprocess.run([str(binary/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=60);record.update(log=p.stdout+p.stderr,returncode=p.returncode,status='failed')
 if p.returncode==0:
  def reference(x):
   # Direct DFT at16 checks signs/order independently; recursively factored
   # floating DFT at larger sizes avoids copying RTL fixed-point truncation.
   if n==16:return [sum(v*cmath.exp(-2j*math.pi*k*i/n) for i,v in enumerate(x))/n for k in range(n)]
   def transform(a):
    if len(a)==1:return a
    even=transform(a[::2]);odd=transform(a[1::2]);tw=[cmath.exp(-2j*math.pi*k/len(a))*v for k,v in enumerate(odd)]
    return [u+v for u,v in zip(even,tw)]+[u-v for u,v in zip(even,tw)]
   return [v/n for v in transform(x)]
  rows=[tuple(map(int,line.split())) for line in (o/'bins.txt').read_text().splitlines()]
  assert len(rows)==6*n
  metrics=[]
  for f,x in enumerate(inputs[:5]):
   values=rows[f*n:(f+1)*n];assert all(row[0]==f and row[1]==i for i,row in enumerate(values))
   expected=reference(x);actual=[complex(row[2],row[3]) for row in values]
   error=max(max(abs(a.real-e.real),abs(a.imag-e.imag)) for a,e in zip(actual,expected))
   metrics.append(dict(frame=f,max_component_error_lsb=error,largest_bin=max(range(n),key=lambda k:abs(actual[k]))))
  record['metrics']=metrics;record['tolerance_lsb']=2*log_n+2
  record['status']='passed' if all(m['max_component_error_lsb']<=record['tolerance_lsb'] for m in metrics) and metrics[1]['largest_bin']==7 and all(row[2:]==(0,0) for row in rows[4*n:5*n]) else 'failed'
(o/'result.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='sources'},indent=2));sys.exit(0 if record['status']=='passed' else 1)
