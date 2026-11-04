"""Actual async PCM snapshot/Hann/FFT chain versus floating DFT, every bin."""
from pathlib import Path
import math,cmath,sys,os,subprocess,json,hashlib
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/audio_visual'
n=int(sys.argv[1]) if len(sys.argv)>1 else 2048
assert n in (16,512,2048)
o=b/'evidence/pcm_spectrum'/str(n);o.mkdir(parents=True,exist_ok=True)
k=3 if n==16 else 13
samples=[round(16000*math.cos(2*math.pi*k*i/n)+3000*math.sin(2*math.pi*(k+2)*i/n)) for i in range(n)]
(o/'input.hex').write_text('\n'.join(f'{v&65535:04x}' for v in samples)+'\n')
tb='''`timescale 1ns/1ps
module tb;
localparam N=@N@,LOG_N=@LOG@;
reg ac=0,dc=0,run=0;always #7 ac=~ac;always #5 if(run)dc=~dc;
reg rst=1,pv=0,ready=0;reg signed[15:0]l=0,r=0;
wire valid;wire[LOG_N-1:0]bin;wire signed[15:0]yr,yi;
wire[31:0]frame,last,skipped,clips;wire[16:0]pl,pr;
reg[15:0]data[0:N-1];integer i,j,file,audio_count=0,before_count;
reg signed[15:0]held_r,held_i;
pcm_spectrum #(.LOG_N(LOG_N),.TWIDDLE_FILE("@TW@"),.WINDOW_FILE("@WIN@")) dut(
ac,dc,rst,pv,l,r,valid,ready,bin,yr,yi,frame,last,pl,pr,skipped,clips);
always @(posedge ac)if(!rst&&pv)audio_count=audio_count+1;
initial begin
 $readmemh("@IN@",data);file=$fopen("@OUT@","w");
 run=1;repeat(3)@(negedge dc);rst=0;run=0;
 // Samples presented during the documented reset-release window are not accepted.
 wait(!dut.capture.write_reset);
 for(i=0;i<N;i=i+1)begin @(negedge ac);pv=1;l=data[i];r=-1234;end
 @(negedge ac);l=0;r=0;
 repeat(64)@(negedge ac);if(skipped<64)$fatal(1,"stopped analysis clock did not count skipped visual samples");
 run=1;wait(valid);@(negedge dc);
 if(frame!=1||last!=N-1||pl!=@PEAK@||pr!=1234)$fatal(1,"metadata not bound to first window");
 before_count=audio_count;
 for(j=0;j<N;j=j+1)begin
  while(!valid)@(negedge dc);
  if(bin!=j)$fatal(1,"bin order");held_r=yr;held_i=yi;
  if(j%17==0)repeat(20)begin
   @(negedge dc);if(!valid||bin!=j||yr!==held_r||yi!==held_i||frame!=1||last!=N-1)$fatal(1,"stalled spectrum changed");
  end
  $fwrite(file,"%0d %0d %0d\\n",j,$signed(yr),$signed(yi));ready=1;@(negedge dc);ready=0;
 end
 if(audio_count<=before_count||clips||dut.rejected)$fatal(1,"continuity/clips/start");
 // Shared reset invalidates snapshots, partial transforms, and stale metadata.
 wait(valid);@(negedge dc);run=0;pv=0;rst=1;repeat(3)@(negedge ac);rst=0;
 if(valid)$fatal(1,"reset while clock stopped exposed stale FFT result");
 repeat(3)@(negedge ac);run=1;repeat(6)@(negedge dc);
 if(valid||frame||last||pl||pr||skipped)$fatal(1,"reset stale data");
 $fclose(file);$display("PASS PCM/Hann/FFT N=%0d asynchronous clocks,stopped analysis,output stalls,metadata,reset,audio continued",N);$finish;
end
initial begin #100000000;$fatal(1,"timeout");end
endmodule
'''
for key,value in {'N':n,'LOG':n.bit_length()-1,'TW':(s/f'fft_twiddle_{n}.mem').as_posix(),'WIN':(s/f'hann_{n}.mem').as_posix(),'IN':(o/'input.hex').as_posix(),'OUT':(o/'bins.txt').as_posix(),'PEAK':max(map(abs,samples))}.items():tb=tb.replace('@'+key+'@',str(value))
(o/'tb.v').write_text(tb)
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
files=[s/p for p in ('pcm_snapshot.v','fft_fixed.v','pcm_spectrum.v')]
record=dict(status='failed',n=n,scope='PCM-snapshot/Hann/FFT RTL integration only, synthetic PCM; no fullband synthesis/timing/display/physical acceptance')
c=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(o/'test.vvp'),*map(str,files),str(o/'tb.v')],env=env,capture_output=True,text=True)
record['compile_log']=c.stdout+c.stderr
if c.returncode==0:
 p=subprocess.run([str(binary/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=60);record['log']=p.stdout+p.stderr
 if p.returncode==0:
  window=[int(x,16) for x in (s/f'hann_{n}.mem').read_text().split()]
  x=[complex((v*w)//32768,0) for v,w in zip(samples,window)]
  def dft(a):
   if len(a)==1:return a
   even,odd=dft(a[::2]),dft(a[1::2]);half=len(a)//2
   factors=[cmath.exp(-2j*math.pi*k/len(a))*odd[k] for k in range(half)]
   return [even[k]+factors[k] for k in range(half)]+[even[k]-factors[k] for k in range(half)]
  ref=[v/n for v in dft(x)];rows=[list(map(int,line.split())) for line in (o/'bins.txt').read_text().splitlines()]
  assert len(rows)==n
  error=max(max(abs(re-ref[k].real),abs(im-ref[k].imag)) for k,re,im in rows)
  assert error<=24,error
  record.update(status='passed',max_component_error_lsb=error)
deps=files+[s/f'hann_{n}.mem',s/f'fft_twiddle_{n}.mem',o/'tb.v',o/'input.hex',Path(__file__)]
record['sources']={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in deps}
(o/'result.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='sources'},indent=2));raise SystemExit(record['status']!='passed')
