"""Exercise saved pad calibration in the actual exported stage RTL."""
from pathlib import Path
import json,sys,os,subprocess,hashlib,datetime,shutil
r=Path(__file__).resolve().parents[3];b=r/'synth/band';sys.path.insert(0,str(b/'host'))
from offline_workstation import export_workstation_project
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
out=b/'evidence/stage_export_calibration'/stamp;out.mkdir(parents=True)
target=Path('D:/StarclusterBuilds')/('stage_calibration_export_'+stamp)
score=dict(format='starcluster-score-2',engine_profile='singer-v1',sample_rate=48000,bpm=120,duration_samples=192,
 events=[dict(sample=0,kind=0,part=0,note=36,velocity=80,serial=1),dict(sample=96,kind=1,part=0,note=36,velocity=0,serial=1)],
 performance=dict(pad_calibration={'0':dict(baseline=100,gain=4096,invert=True),'63':dict(baseline=50,gain=2048,invert=False)}))
export_workstation_project(score,target,True)
source=target/'rtl/stage_pad_frontend.sv';shutil.copy2(source,out/source.name)
(out/'score.json').write_text(json.dumps(score,indent=2))
tb='''`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,sv=0,cfg=0;reg[2:0]ch=0;reg[119:0]samples=0;
 wire[559:0]values;
 stage_pad_frontend dut(.clk(clk),.rst(rst),.panic(panic),.sample_valid(sv),.sample_channel(ch),.samples(samples),
 .config_valid(cfg),.config_channel(7'd0),.config_baseline(12'd0),.config_gain(16'd4096),.config_invert(1'b0),
 .on_threshold(7'd24),.off_threshold(7'd12),.event_ready(1'b0),.pressure_values(values));
 task frame(input[2:0]channel,input[11:0]first,last);
 begin @(negedge clk);ch=channel;samples=0;samples[11:0]=first;samples[7*12+:12]=last;samples[9*12+:12]=4095;sv=1;
 @(negedge clk);sv=0;wait(!dut.busy);repeat(2)@(negedge clk);end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;
  frame(0,3990,0);if(values[6:0]!=5)$fatal(1,"saved inverted pad0 default lost");
  frame(7,0,100);if(values[63*7+:7]!=25||values[79*7+:7]!=126)$fatal(1,"pad63/default lane calibration lost");
  @(negedge clk);cfg=1;@(negedge clk);cfg=0;
  frame(0,20,0);if(values[6:0]!=20)$fatal(1,"live calibration override lost");
  panic=1;@(negedge clk);panic=0;
  frame(0,20,0);if(values[6:0]!=20)$fatal(1,"panic erased live calibration");
  rst=1;repeat(2)@(negedge clk);rst=0;
  frame(0,3990,0);if(values[6:0]!=5)$fatal(1,"reset failed to restore saved calibration");
  frame(7,0,100);if(values[63*7+:7]!=25)$fatal(1,"reset failed pad63 saved calibration");
  $display("PASS actual exported calibration:pad0 inversion,pad63 gain,default channel79,live override,panic preserve,reset saved defaults");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
'''
(out/'tb.v').write_text(tb)
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
c=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(out/'test.vvp'),str(source),str(out/'tb.v')],env=env,capture_output=True,text=True,timeout=60)
(out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
p=subprocess.run([str(binary/'vvp.exe'),str(out/'test.vvp')],env=env,capture_output=True,text=True,timeout=60)
record=dict(status='passed' if p.returncode==0 and 'PASS actual exported calibration' in p.stdout else 'failed',returncode=p.returncode,log=p.stdout+p.stderr,export=str(target),scope='Actual exported stage calibration RTL;not physical boot,whole-top timing or musical acceptance',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),export_manifest_sha256=hashlib.sha256((target/'export_manifest.json').read_bytes()).hexdigest())
(out/'result.json').write_text(json.dumps(record,indent=2));print(record['status'],record['log']);raise SystemExit(record['status']!='passed')
