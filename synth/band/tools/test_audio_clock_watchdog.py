"""Missing-clock fail-closed startup, qualified recovery and one loss per outage."""
from pathlib import Path
import os,subprocess,json,hashlib
r=Path(__file__).resolve().parents[3];b=r/'synth/band';o=b/'evidence/audio_clock_watchdog';o.mkdir(exist_ok=True)
rtl=b/'experimental/audio_input/audio_clock_watchdog.v'
tb='''`timescale 1ns/1ps
module tb;
reg clk=0,ac=0,run=0,rst=1;always #10 clk=~clk;always #7 if(run)ac=~ac;
wire fault;wire[31:0]losses;
audio_clock_watchdog #(.DIV_BITS(2),.TIMEOUT_CYCLES(50)) dut(clk,ac,rst,fault,losses);
initial begin
 repeat(4)@(negedge clk);rst=0;repeat(80)@(negedge clk);
 if(!fault||losses)$fatal(1,"missing startup clock must stay muted");
 run=1;wait(dut.recovery==1);@(negedge ac);run=0;
 repeat(80)@(negedge clk);if(!fault||losses||dut.recovery)$fatal(1,"isolated pulse train must not qualify recovery");
 run=1;wait(!fault);@(negedge ac);run=0;repeat(4)@(negedge clk);
 if(fault)$fatal(1,"brief gap below timeout");run=1;repeat(40)@(negedge clk);
 @(negedge ac);run=0;repeat(80)@(negedge clk);
 if(!fault||losses!=1)$fatal(1,"first outage");repeat(100)@(negedge clk);
 if(losses!=1)$fatal(1,"outage counted repeatedly");run=1;wait(!fault);
 @(negedge ac);run=0;repeat(80)@(negedge clk);if(!fault||losses!=2)$fatal(1,"second outage");
 rst=1;repeat(4)@(negedge clk);rst=0;repeat(5)@(negedge clk);
 if(!fault||losses)$fatal(1,"reset while audio clock absent");
 $display("PASS audio-clock watchdog:missing startup,three-toggle recovery,brief gap,two outages counted once,stopped-clock reset");$finish;
end
initial begin #100000;$fatal(1,"timeout");end
endmodule
'''
(o/'tb.v').write_text(tb);binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
logs=[];ok=True
for command in ([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(o/'test.vvp'),str(rtl),str(o/'tb.v')],[str(binary/'vvp.exe'),str(o/'test.vvp')]):
 p=subprocess.run(command,env=env,capture_output=True,text=True,timeout=30);logs.append(p.stdout+p.stderr)
 if p.returncode:ok=False;break
record=dict(status='passed' if ok and 'PASS' in logs[-1] else 'failed',scope='Digital missing-edge detector RTL; no frequency/PLL quality,physical clock or analog mute claim',sources={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (rtl,o/'tb.v',Path(__file__))},log=''.join(logs))
(o/'result.json').write_text(json.dumps(record,indent=2));print(record['log']);raise SystemExit(record['status']!='passed')
