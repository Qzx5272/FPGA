`timescale 1ns/1ps
module tb_panel_v6;
 reg clk=0;always #5 clk=~clk;
 reg rst=1;reg a=0,b=0;wire up,down;wire[31:0]errors;
 integer ups=0,downs=0;
 quadrature_encoder #(.STABLE_CYCLES(2)) encoder(clk,rst,a,b,up,down,errors);
 always @(posedge clk)begin if(up)ups<=ups+1;if(down)downs<=downs+1;end
 reg[7:0]ea=0,eb=0;wire pv;reg pr=0;wire[223:0]pp;wire[3:0]part;wire[111:0]values;
 panel_controls #(.DEBOUNCE(2)) panel(clk,rst,ea,eb,pv,pr,pp,part,values);
 task state(input[1:0]s);begin @(negedge clk);{a,b}=s;repeat(10)@(negedge clk);end endtask
 task knob(input[1:0]s);begin @(negedge clk);{ea[0],eb[0]}=s;repeat(10)@(negedge clk);end endtask
 reg[223:0]held;
 initial begin
 repeat(4)@(negedge clk);rst=0;
 state(1);state(3);state(2);state(0);if(ups!=1||downs!=0)$fatal(1,"forward");
 state(2);state(3);state(1);state(0);if(ups!=1||downs!=1)$fatal(1,"reverse");
 state(3);if(errors!=1)$fatal(1,"illegal transition");state(0);
 // Sub-debounce contact chatter cannot form a detent.
 @(negedge clk);a=1;@(negedge clk);a=0;repeat(12)@(negedge clk);
 if(ups!=1||downs!=1)$fatal(1,"bounce");
 knob(1);knob(3);knob(2);knob(0);wait(pv);@(negedge clk);held=pp;
 if(pp[15:8]!=10||pp[223:192]!=65)$fatal(1,"master payload");
 knob(1);knob(3);knob(2);knob(0);
 if(pp!==held)$fatal(1,"backpressure changed payload");
 pr=1;@(negedge clk);pr=0;wait(pv);@(negedge clk);
 if(pp[223:192]!=66)$fatal(1,"coalesced knob update");
 $display("PASS panel: Gray directions,invalid transition,debounce,master range,backpressure,coalescing");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
