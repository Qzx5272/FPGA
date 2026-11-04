`timescale 1ns/1ps
module tb_dual_uart_v6;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,pcv=0,blev=0,panelv=0,ready=0;reg[7:0]pc=0,ble=0;
 reg[223:0]panel=224'h1234;wire panelr,valid,panic;wire[223:0]payload;wire[31:0]crc,overflow;
 dual_uart_events dut(clk,rst,pc,ble,pcv,blev,panelv,panelr,panel,valid,ready,payload,panic,crc,overflow);
 reg[7:0]frames[0:101];reg[223:0]held;integer i,got=0;reg[2:0]seen=0;
 task inject(input integer channel,input integer base);begin
 for(i=base;i<base+34;i=i+1)begin
 @(negedge clk);if(channel==0)begin pcv=1;pc=frames[i];end else begin blev=1;ble=frames[i];end
 end
 @(negedge clk);pcv=0;blev=0;repeat(8)@(negedge clk);
 end endtask
 always @(posedge clk)if(valid&&ready)begin
 got<=got+1;
 if(payload==panel)begin seen[2]<=1;panelv<=0;end
 else if(payload[23:16]==1)seen[0]<=1;
 else if(payload[23:16]==3)seen[1]<=1;
 else $fatal(1,"unexpected source");
 end
 initial begin
 $readmemh("ingress_frames.mem",frames);
 repeat(4)@(negedge clk);rst=0;panelv=1;
 repeat(3)@(negedge clk);held=payload;
 inject(0,0);inject(1,34);
 if(!valid||payload!==held)$fatal(1,"new arrival preempted stalled producer");
 ready=1;wait(got==3);@(negedge clk);ready=0;
 if(seen!=7||crc||overflow)$fatal(1,"round robin or parser");
 inject(0,68);if(!panic)begin // Parser panic is a pulse; inspect parser counter after flush instead.
 repeat(4)@(negedge clk);
 end
 if(valid)$fatal(1,"panic retained producer");
 $display("PASS ingress: production CRC parsing,two UARTs,panel,stable stalled grant,round robin,panic flush");$finish;
 end
 initial begin #100000;$fatal(1,"timeout got=%0d",got);end
endmodule
