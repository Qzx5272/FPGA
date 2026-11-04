`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg kp=1,ks=1,ke=1;
wire bck,ws,din;
GSR GSR(.GSRI(1'b1));
board_pt8211_controls_top dut(.clk(clk),.uart_rx_pin(1'b1),
 .key_play_n(kp),.key_stop_n(ks),.key_panic_n(ke),.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din));
// Accelerated debounce only. The production default remains250000cycles.
defparam dut.workstation.band.engine.local_inputs.play_button.STABLE_CYCLES=4;
defparam dut.workstation.band.engine.local_inputs.stop_button.STABLE_CYCLES=4;
integer np=0,ns=0;
always @(negedge clk)begin
 if(dut.workstation.band.engine.local_play_pulse)np=np+1;
 if(dut.workstation.band.engine.local_stop_pulse)ns=ns+1;
end
task settle;begin repeat(100)@(negedge clk);end endtask
initial begin
 wait(!dut.workstation.band.engine.rst);
 wait(dut.workstation.band.engine.playing);settle;
 if(np||ns||dut.workstation.band.engine.panic)$fatal(1,"idle keys asserted");
 // One-clock bounce must not stop transport.
 ks=0;@(negedge clk);ks=1;settle;
 if(ns||!dut.workstation.band.engine.playing)$fatal(1,"bounce accepted");
 ks=0;settle;
 if(ns!=1||dut.workstation.band.engine.playing)$fatal(1,"stop press/hold");
 settle;if(ns!=1)$fatal(1,"held stop repeated");
 ks=1;settle;kp=0;settle;
 if(np!=1||!dut.workstation.band.engine.playing)$fatal(1,"play press");
 settle;if(np!=1)$fatal(1,"held play repeated");
 kp=1;settle;ke=0;repeat(4)@(negedge clk);
 if(!dut.workstation.band.engine.panic)$fatal(1,"panic synchronizer");
 settle;
 if(dut.workstation.band.engine.playing||dut.workstation.band.engine.active_voices!=0)$fatal(1,"panic failed to clear");
 kp=0;settle;
 if(dut.workstation.band.engine.playing)$fatal(1,"play escaped held panic");
 kp=1;ke=1;settle;
 if(dut.workstation.band.engine.playing)$fatal(1,"panic release restarted");
 kp=0;settle;
 if(!dut.workstation.band.engine.playing||np!=3)$fatal(1,"fresh play failed");
 ks=0;settle;
 if(dut.workstation.band.engine.playing||ns!=2)$fatal(1,"final stop failed");
 $display("PASS actual board shell: idle,bounce,hold,stop,play,panic priority,no auto resume,fresh restart");$finish;
end
initial begin #4000000;$fatal(1,"timeout");end
endmodule
