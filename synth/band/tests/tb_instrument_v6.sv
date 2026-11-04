`timescale 1ns/1ps
module tb_instrument_v6;
 reg clk=0;always #5 clk=~clk;reg rst=1,tick=0,ev=0,cv=0;wire er,valid;
 reg[3:0]param=8;reg[13:0]value=8;reg[7:0]contact=1;reg[31:0]serial=1;
 wire[16*70-1:0]patches;wire signed[15:0]left,right;wire[15:0]voices,cycles;wire[31:0]rejected,deadline,clips;
 shared_role_controls controls(clk,rst,tick,cv,4'd6,param,value,1'b0,4'd0,patches);
 central_voice_bank bank(clk,rst,1'b0,tick,ev,er,2'd0,8'd1,contact,4'd6,32'd1,serial,7'd60,7'd100,
 valid,left,voices,cycles,rejected,deadline,clips,1'b0,,,,,right,1'b0,4'd0,4'd0,14'd0,patches);
 task parameter_set(input[3:0]p,input[13:0]v);begin @(negedge clk);param=p;value=v;cv=1;@(negedge clk);cv=0;end endtask
 task note;begin @(negedge clk);wait(er);ev=1;@(negedge clk);ev=0;repeat(50)@(negedge clk);end endtask
 task frame;begin @(negedge clk);tick=1;@(negedge clk);tick=0;wait(valid);@(negedge clk);end endtask
 integer i;
 initial begin
 repeat(4)@(negedge clk);rst=0;parameter_set(8,8);parameter_set(6,14000);note();frame();frame();
 if(bank.renderer.state_memory[2][28:25]!=8)$fatal(1,"initial instrument mapping");
 parameter_set(8,9);frame();
 if(bank.renderer.state_memory[2][28:25]!=8)$fatal(1,"preset switch changed old voice algorithm");
 contact=2;serial=2;note();frame();
 if(bank.renderer.state_memory[5][28:25]!=9||voices!=2)$fatal(1,"new note did not use new algorithm");
 parameter_set(9,0);for(i=0;i<80;i=i+1)frame();
 if(controls.pan[6]!=0||right!=0||left==0)$fatal(1,"left pan");
 parameter_set(9,127);for(i=0;i<140;i=i+1)frame();
 if(controls.pan[6]!=127||left!=0||right==0)$fatal(1,"right pan");
 if(deadline||clips||rejected)$fatal(1,"counters deadline=%0d clips=%0d rejected=%0d",deadline,clips,rejected);
 $display("PASS per-track instruments: independent role/algorithm,old voice keeps algorithm,new voice changes,smooth pan left/right,zero deadline/clip/reject");$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
