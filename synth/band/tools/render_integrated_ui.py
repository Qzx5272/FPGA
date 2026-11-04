from pathlib import Path
import argparse,subprocess,os
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--build',required=True);a=p.parse_args();b=Path(a.build)
root=Path(__file__).resolve().parents[3];cad=root/'tmp/oss-cad-suite';env=dict(os.environ)
env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH']
tb='''`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1;always #20 clk=~clk;
 reg[9:0]x=0,y=0;reg active=0;reg[127:0]state=0;wire[23:0]rgb;wire de,hs,vs;
 instrument_ui dut(clk,rst,x,y,active,1'b1,1'b1,state,rgb,de,hs,vs);
 integer page,f,xx,yy,n;reg capture=0;string name;
 always @(negedge clk)if(capture&&de)begin
  if(^rgb===1'bx)$fatal(1,"unknown pixel");
  $fwrite(f,"%d %d %d\\n",rgb[23:16],rgb[15:8],rgb[7:0]);n=n+1;
 end
 initial begin
  state[0]=1;state[7:1]=64;state[15:8]=120;state[31:16]=4;state[38:32]=60;
  state[45:39]=100;state[49:46]=8;state[65:50]=16'h1234;state[66]=1;
  state[80:67]=1024;state[84:81]=7;state[85]=1;state[89:86]=9;
  state[102:99]=8;state[106:103]=-2;state[110:109]=2;state[111]=1;state[112]=1;
  state[116:113]=5;state[123:117]=100;state[125:124]=1;
  for(page=0;page<5;page=page+1)begin
   capture=0;rst=1;repeat(5)@(negedge clk);rst=0;state[108:107]=page==4?2:page;
   if(page==4)begin state[110:109]=3;state[106:103]=0;state[112]=0;state[123:117]=110;end
   name=$sformatf("ui_page_%0d.ppm",page);f=$fopen(name,"w");$fwrite(f,"P3\\n640 480\\n255\\n");n=0;capture=1;
   for(yy=0;yy<480;yy=yy+1)for(xx=0;xx<640;xx=xx+1)begin @(posedge clk);#1;x=xx;y=yy;active=1;end
   @(posedge clk);#1;active=0;repeat(5)@(posedge clk);#1;
   if(n!=640*480)$fatal(1,"pixel count %d",n);capture=0;$fclose(f);
  end
  $display("PASS four UI pages, including an additional lesson view, no unknown pixels, 640x480 each");$finish;
 end
endmodule
'''
module='instrument_ui.v'
if (b/'rtl/score_layout.vh').exists():
    module='score_display.sv'
    tb=tb.replace("instrument_ui dut(clk,rst,x,y,active,1'b1,1'b1,state,rgb,de,hs,vs);",
        """reg[383:0]l=0,r=0;reg[127:0]bands=0;
 score_display dut(clk,rst,active,rst,x,y,state,bands,l,r,6'd22,6'd36,{7'd32,7'd64,7'd80,7'd64},1'b0,1'b0,7'd22,3'd0,{1'b1,4'd4,7'd67,5'd20,7'd18,8'd2},rgb,de);
 initial for(integer i=0;i<64;i++)begin l[i*6+:6]=32+$rtoi(22*$sin(i*0.22));r[i*6+:6]=32+$rtoi(17*$sin(i*0.22+0.7));end
 initial for(integer j=0;j<32;j++)bands[j*4+:4]=j==9?15:j==15?10:j%4;""")
    tb=tb.replace('640','800').replace('page==4?2:page','page==4?3:page').replace('state[49:46]=8','state[49:46]=4').replace('state[125:124]=1','state[125:124]=0').replace('state[110:109]=3;', "state[110:109]=3;state[97]=1;state[96:93]=4;")
(b/'ui_test.sv').write_text(tb)
subprocess.run([str(cad/'bin/iverilog.exe'),'-g2012','-I',str(b/'rtl'),'-s','tb','-o',str(b/'ui_test.vvp'),str(b/'ui_test.sv'),str(b/'rtl'/module)],env=env,check=True)
r=subprocess.run([str(cad/'bin/vvp.exe'),'ui_test.vvp'],cwd=b,env=env,capture_output=True,text=True,timeout=360)
(b/'ui_test.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
for i in range(5):Image.open(b/f'ui_page_{i}.ppm').save(b/f'ui_page_{i}.png')
print(r.stdout)
