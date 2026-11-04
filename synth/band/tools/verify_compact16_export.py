"""Check the three-ADC export, eight controls and absence of phantom pad events."""
from pathlib import Path
import os,sys,json,subprocess
band=Path(__file__).resolve().parents[1];root=band.parents[1]
sys.path.insert(0,str(band/'host'))
from score import load
from offline_v6 import export_v6_project
target=Path('D:/StarclusterBuilds/v6_compact16_export')
score=load(band/'assets/confluence_v6.json')
export_v6_project(score,target,compact16=True)
rtl=target/'rtl';binary=root/'tmp/oss-cad-suite/bin'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
tb=r'''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst=1,sv=0;reg[2:0]channel=0;reg[119:0]samples=0;
wire valid;wire[3:0]part,parameter_id;wire[13:0]value;
local_expression expression(clk,rst,1'b0,sv,channel,samples,valid,1'b1,part,parameter_id,value);
wire ev,off;wire[6:0]contact,pressure;wire[31:0]serial,overruns;wire[559:0]pressures;wire exhausted;
stage_pad_frontend #(.PADS(16)) pads(clk,rst,1'b0,sv,channel,samples,
 1'b0,7'd0,12'd0,16'd127,1'b0,7'd24,7'd12,ev,1'b1,off,contact,pressure,serial,pressures,overruns,exhausted);
integer changes=0,presses=0,releases=0;reg[7:0]seen=0;integer c;integer address;
always @(posedge clk)if(!rst)begin
 if(valid)begin
  case(part)6:address=0;3:address=1;4:address=2;7:address=3;default:$fatal(1,"bad control role");endcase
  if(parameter_id!=0)address=address+4;
  if(address==7&&parameter_id!=2)$fatal(1,"missing vowel control");
  if(address>=4&&address<7&&parameter_id!=1)$fatal(1,"missing bend control");
  if(seen[address])$fatal(1,"duplicate control");seen[address]=1;changes=changes+1;
 end
 if(ev)begin
  if(contact!=15)$fatal(1,"phantom pad from analog ADC or missing lane");
  if(off)releases=releases+1;else presses=presses+1;
 end
end
task scan(input[2:0]ch,input[11:0]analog,input[11:0]pad15);
begin @(negedge clk);channel=ch;samples=0;samples[35:24]=analog;
 if(ch==7)samples[23:12]=pad15;sv=1;@(negedge clk);sv=0;repeat(80)@(negedge clk);end endtask
initial begin
 repeat(5)@(negedge clk);rst=0;
 for(c=0;c<8;c=c+1)scan(c,1000,0);
 for(c=0;c<8;c=c+1)scan(c,3000,0);
 if(changes!=8||seen!=8'hff||presses!=0||releases!=0)$fatal(1,"compact mapping incorrect");
 scan(7,3000,4095);scan(7,3000,0);
 if(presses!=1||releases!=1||overruns!=0)$fatal(1,"pad15 press/release failed");
 $display("PASS compact16: eight controls, pad15 and no analog phantom pads");$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
'''
(target/'tb.sv').write_text(tb)
files=[p for p in rtl.iterdir() if p.suffix in ('.v','.sv') and not p.name.startswith('tb_')]
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
commands=[
 [str(binary/'iverilog.exe'),'-g2012','-I',str(rtl),'-s','tb','-o',str(target/'test.vvp'),str(rtl/'local_expression.v'),str(rtl/'stage_pad_frontend.sv'),str(target/'tb.sv')],
 [str(binary/'vvp.exe'),str(target/'test.vvp')],
 [str(binary/'iverilog.exe'),'-g2012','-I',str(rtl),'-s','workstation_v6_complete_top','-s','GSR','-o',str(target/'complete.vvp'),*map(str,files),str(vendor)]]
logs=[]
for command in commands:
 p=subprocess.run(command,cwd=target,env=env,capture_output=True,text=True,timeout=90)
 logs.append(dict(returncode=p.returncode,output=p.stdout+p.stderr))
 if p.returncode:break
passed=len(logs)==3 and all(r['returncode']==0 for r in logs) and 'PASS compact16' in logs[1]['output']
result=dict(status='passed' if passed else 'failed',scope='Three-ADC source export behavior and complete vendor-primitive elaboration only; no PnR or hardware claim',logs=logs)
(target/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
if not passed:raise SystemExit(1)
