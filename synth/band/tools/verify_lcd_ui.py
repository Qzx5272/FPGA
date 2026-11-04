from pathlib import Path
import os,subprocess,json
from PIL import Image
band=Path(__file__).resolve().parents[1];root=band.parents[1];build=Path('D:/StarclusterBuilds/lcd_ui_20261031_a')
out=root/'tmp/lcd_ui_tests';out.mkdir(exist_ok=True)
text=(build/'rtl/band_stage_pt8211_engine.sv').read_text();header=text[text.index('module band_stage_pt8211_engine'):].split(');',1)[0]+');'
stub=header+'''\nassign reset_out=0;assign panic_out=0;assign audio_stop=0;
assign ui_snapshot_data={29'd0,32'd1,1'b1,16'h0420,4'd8,7'd98,7'd70,16'd2,8'd120,7'd64,1'b0};
endmodule
module Gowin_PLL(output reg clkout0=0,input clkin,output lock_o);always #20 clkout0=~clkout0;assign lock_o=1;endmodule
'''
(out/'stubs.sv').write_text(stub)
cad=root/'tmp/oss-cad-suite';env=dict(os.environ);env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH']
ui=band/'experimental/hdmi_ui';lcd=band/'experimental/lcd_ui';exe=out/'tb.vvp'
cmd=[str(cad/'bin/iverilog.exe'),'-g2012','-I',str(ui),'-s','tb_lcd_ui','-o',str(exe),str(lcd/'tb_lcd_ui.sv'),str(out/'stubs.sv'),str(lcd/'board_lcd_ui_top.sv'),str(ui/'instrument_ui.v'),str(ui/'ui_state.v')]
subprocess.run(cmd,env=env,check=True)
p=subprocess.run([str(cad/'bin/vvp.exe'),str(exe)],env=env,cwd=ui,capture_output=True,text=True,timeout=180)
e=band/'evidence/lcd_ui_20261031';e.mkdir(exist_ok=True);(e/'pixel_test.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout+p.stderr
Image.open(ui/'lcd_ui_frame.ppm').save(e/'ui_preview.png');print(p.stdout)
