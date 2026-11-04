"""Decode vendor OSER10/ELVDS serial pins against independently encoded pixels."""
from pathlib import Path
import os,sys,subprocess,json,hashlib,datetime
r=Path(__file__).resolve().parents[3];b=r/'synth/band';src=b/'experimental/audio_visual/dvi'
if '--source-dir' in sys.argv:
 src=Path(sys.argv[sys.argv.index('--source-dir')+1]).resolve()
sys.path.insert(0,str(b/'reference'));from tmds_reference import encode,control
clocked='--clocked' in sys.argv[1:]
out=b/('evidence/gowin_dvi_clocked' if clocked else 'evidence/gowin_dvi_tx')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
count=1200;stimuli=[];symbols=[[],[],[]];disparity=[0,0,0]
for i in range(count):
 resetn=i>=5 and not 600<=i<605;de=i%29<24;hs=i%7<3;vs=i%17<8
 rgb=((i*79&255)<<16)|((i*131&255)<<8)|(i*37&255)
 stimuli.append((int(resetn)<<27)|(int(de)<<26)|(int(hs)<<25)|(int(vs)<<24)|rgb)
 for lane in range(3):
  if not resetn:word=0;disparity[lane]=0
  elif not de:word=control[(int(vs)*2+int(hs)) if lane==0 else 0];disparity[lane]=0
  else:word,disparity[lane]=encode((rgb>>(lane*8))&255,disparity[lane])
  symbols[lane].append(word)
(out/'stimulus.hex').write_text(''.join(f'{x:07x}\n' for x in stimuli))
tb='''`timescale 1ns/1ps
module tb;
reg pc=0,sc=0;always #20 pc=~pc;always #4 sc=~sc;
reg[27:0]s=0;reg[27:0]stimulus[0:1199];integer i,fd,n=0;
wire cp,cn;wire[2:0]dp,dn;
GSR GSR(.GSRI(1'b1));
gowin_dvi_tx dut(pc,sc,s[27],s[26],s[25],s[24],s[23:0],cp,cn,dp,dn);
always @(posedge sc or negedge sc)begin
 #1;if(cp!==pc||cn!==!pc||dn!==~dp)$fatal(1,"differential pins or clock polarity");
 $fdisplay(fd,"%0d %b",n,dp);n=n+1;
end
initial begin
fd=$fopen("serial.txt","w");$readmemh("stimulus.hex",stimulus);
for(i=0;i<1200;i=i+1)begin @(negedge pc);s=stimulus[i];end
repeat(16)@(negedge pc);$fclose(fd);$finish;
end
endmodule
'''
if clocked:
 tb=tb.replace('reg pc=0,sc=0;always #20 pc=~pc;always #4 sc=~sc;',
  "reg clk50=0,clock_resetn=0;always #10 clk50=~clk50;wire pc,sc,clock_ready,clock_locked;\n"
  "gowin_video_clock clocks(clk50,clock_resetn,sc,pc,clock_locked,clock_ready);\ninitial begin #100;clock_resetn=1;end")
 tb=tb.replace('dut(pc,sc,s[27],','dut(pc,sc,s[27]&&clock_ready,')
 tb=tb.replace('#1;if(cp', '#1;if(clock_ready)begin if(cp').replace('n=n+1;\nend','n=n+1;end\nend')
 tb=tb.replace('$readmemh("stimulus.hex",stimulus);','$readmemh("stimulus.hex",stimulus);wait(clock_ready);')
(out/'tb.v').write_text(tb)
names=['starcluster_tmds_encoder.v','dvi_symbols.v','gowin_dvi_tx.v']+(['gowin_video_clock.v'] if clocked else [])
for name in names:(out/name).write_bytes((src/name).read_bytes())
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
compiled=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o','sim.vvp','tb.v',*names,str(vendor)],cwd=out,env=env,capture_output=True,text=True)
run=subprocess.run([str(binary/'vvp.exe'),'sim.vvp'],cwd=out,env=env,capture_output=True,text=True) if compiled.returncode==0 else None
record=dict(status='failed',scope='Vendor OSER10+ELVDS models at25MHz/125MHz:independent three-lane serial bitstream,RGB/sync mapping,reset/recovery,complementary pins. No PLL/25.2MHz timing/physical/HDMI audio acceptance.',compile_log=compiled.stdout+compiled.stderr,simulation_log=(run.stdout+run.stderr) if run else None)
if clocked:record['scope']='Vendor PLL/CLKDIV/OSER10/ELVDS from50MHz input,target25.2/126MHz:three serial lanes checked against independent pixel encoding,reset/recovery. No PnR,physical jitter/display/HDMI audio acceptance.'
try:
 assert run and run.returncode==0,record
 samples=[line.split()[1] for line in (out/'serial.txt').read_text().splitlines()]
 matches=[]
 for start,end in [(20,580),(625,1180)]:
  offsets=[]
  for lane in range(3):
   bits=''.join(s[2-lane] for s in samples)
   expected=''.join(''.join(str((word>>bit)&1) for bit in range(10)) for word in symbols[lane][start:end])
   offset=bits.find(expected);assert offset>=0,(start,end,lane,'serial stream mismatch')
   latency=offset-start*10;assert 0<=latency<=120,(lane,latency)
   offsets.append(offset)
  assert len(set(offsets))==1,('RGB lanes misaligned',offsets)
  matches.append(dict(first_pixel=start,last_pixel_exclusive=end,serial_offset=offsets[0],matched_bits_per_lane=(end-start)*10))
 record.update(status='passed',segments=matches)
finally:
 record['sources']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [*out.glob('*.v'),out/'stimulus.hex',vendor,b/'reference/tmds_reference.py',Path(__file__)]}
 (out/'result.json').write_text(json.dumps(record,indent=2));print(out);print(json.dumps(record,indent=2))
