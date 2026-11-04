"""Elaborate and inspect the no-ADC USB-pad/encoder configuration."""
from pathlib import Path
import json,os,subprocess,sys
band=Path(__file__).resolve().parents[1];root=band.parents[1];sys.path.insert(0,str(band/'host'))
from score import load
from offline_v6 import export_v6_project
target=Path('D:/StarclusterBuilds/v6_usb16_export')
export_v6_project(load(band/'assets/confluence_v6.json'),target,usb16=True)
rtl=target/'rtl';binary=root/'tmp/oss-cad-suite/bin';env=dict(os.environ)
env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
(target/'tb.sv').write_text('''`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg audio_clk=0;always #20 audio_clk=~audio_clk;
workstation_v6_complete_top dut(.clk(clk),.audio_clk(audio_clk),.pc_rx(1'b1),.ble_rx(1'b1),.usb_rx(1'b1),
 .enc_a(8'd0),.enc_b(8'd0),.mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.song_next(1'b0));
initial begin
 repeat(20)@(negedge clk);
 if(dut.audio.engine.LOCAL_INPUTS!=0)$fatal(1,"analog frontend not disabled");
 if(dut.audio.engine.adc_dout!==10'd0||dut.audio.engine.local_held!==64'd0||dut.audio.engine.local_mv!==1'b0)$fatal(1,"unwired analog input can generate notes");
 if(dut.audio.engine.controls.selected_part!==4'd6)$fatal(1,"digital encoder panel removed");
 $display("PASS USB16 no ADC inputs, no analog note source, digital encoder panel retained");$finish;
end
endmodule
''')
files=[p for p in rtl.iterdir() if p.suffix in ('.v','.sv') and not p.name.startswith('tb_')]
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v');logs=[]
for command in ([str(binary/'iverilog.exe'),'-g2012','-I',str(rtl),'-s','tb','-s','GSR','-o',str(target/'test.vvp'),*map(str,files),str(vendor),str(target/'tb.sv')],
 [str(binary/'vvp.exe'),str(target/'test.vvp')]):
 p=subprocess.run(command,cwd=target,env=env,capture_output=True,text=True,timeout=90);logs.append(dict(returncode=p.returncode,output=p.stdout+p.stderr))
 if p.returncode:break
passed=len(logs)==2 and all(p['returncode']==0 for p in logs) and 'PASS USB16' in logs[1]['output']
result=dict(status='passed' if passed else 'failed',scope='Complete vendor-primitive elaboration and reset-state digital panel/no-ADC inspection only; no USB enumeration, PnR or hardware acceptance',logs=logs)
(target/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if not passed:raise SystemExit(1)
