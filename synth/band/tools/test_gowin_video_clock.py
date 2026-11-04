"""Check PLL/CLKDIV vendor model frequency, exact edge ratio and reset recovery."""
from pathlib import Path
import os,json,hashlib,subprocess,datetime,argparse
r=Path(__file__).resolve().parents[3];b=r/'synth/band';src=b/'experimental/audio_visual/dvi/gowin_video_clock.v'
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=src)
parser.add_argument('--pixel-mhz',type=float,default=25.2)
args=parser.parse_args();src=args.source.resolve()
if not 20 <= args.pixel_mhz <= 30:raise ValueError('Unexpected candidate pixel frequency')
out=b/'evidence/gowin_video_clock'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
tb='''`timescale 1ns/1ps
module tb;
reg clk=0,rstn=0;always #10 clk=~clk;
wire serial,pixel,locked,ready;integer edges=0,start_edges,i,passno;realtime start_time,period;
GSR GSR(.GSRI(1'b1));gowin_video_clock dut(clk,rstn,serial,pixel,locked,ready);
always @(posedge serial)edges=edges+1;
initial begin #1000000;$fatal(1,"PLL lock or measurement timeout");end
initial begin
 #100;rstn=1;
 for(passno=0;passno<2;passno=passno+1)begin
  wait(ready);@(negedge pixel);start_time=$realtime;start_edges=edges;
  for(i=0;i<1000;i=i+1)begin @(negedge pixel);if(!locked||!ready)$fatal(1,"unexpected unlock");end
  period=($realtime-start_time)/1000.0;
  if(period<39.67||period>39.70||edges-start_edges!=5000)$fatal(1,"PLL frequency/ratio period%f edges%0d",period,edges-start_edges);
  $display("PASS segment%0d pixel_period_ns=%f serial_edges=%0d",passno,period,edges-start_edges);
  @(negedge clk);rstn=0;#1;if(ready)$fatal(1,"ready did not clear asynchronously");
  #200;if(ready)$fatal(1,"ready during reset");rstn=1;
 end
 $finish;
end
endmodule
'''
period_ns=1000/args.pixel_mhz
tb=tb.replace('period<39.67||period>39.70',f'period<{period_ns-0.015:.9f}||period>{period_ns+0.015:.9f}')
(out/'tb.v').write_text(tb);(out/src.name).write_bytes(src.read_bytes())
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v');binary=r/'tmp/oss-cad-suite/bin'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
compiled=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o','sim.vvp','tb.v',src.name,str(vendor)],cwd=out,env=env,capture_output=True,text=True)
run=subprocess.run([str(binary/'vvp.exe'),'sim.vvp'],cwd=out,env=env,capture_output=True,text=True,timeout=60) if compiled.returncode==0 else None
record=dict(status='passed' if run and run.returncode==0 else 'failed',scope='VendorPLL/CLKDIV model only:50MHz input,target126MHz/25.2MHz,1000pixels per reset segment,exact5:1 rising-edge ratio,asynchronous ready clear. No jitter/physical lock/PnR/display acceptance.',compile_log=compiled.stdout+compiled.stderr,simulation_log=(run.stdout+run.stderr) if run else None,sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'tb.v',src,vendor,Path(__file__))})
record['scope']=f'Vendor PLL/CLKDIV model only:50MHz input,target{args.pixel_mhz*5}MHz/{args.pixel_mhz}MHz,1000pixels per reset segment,exact5:1 rising-edge ratio,asynchronous ready clear. No jitter/physical lock/PnR/display acceptance.'
record['target_pixel_mhz']=args.pixel_mhz
(out/'result.json').write_text(json.dumps(record,indent=2));print(out);print(json.dumps(record,indent=2));raise SystemExit(record['status']!='passed')
