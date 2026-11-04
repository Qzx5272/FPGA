`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 reg[5:0]a=0,b=0;
 board_lcd_ui_top dut(.clk(clk),.enc_a(a),.enc_b(b),.enc_sw_n(6'h3f),
`ifndef NO_EXTERNAL_PANEL_KEYS
   .panel_key_high(4'd0),
`endif
   .uart_rx_pin(1'b1),.ble_rx(1'b1),.adc_rx(1'b1),.mic_sd(1'b0),.joy_sw_n(1'b1),
   .key_play_n(1'b1),.key_stop_n(1'b1),.key_panic_n(1'b1));
 defparam dut.panel.ENC_STABLE=2;
 task detent(input integer k);
   begin b[k]=1;repeat(10)@(negedge clk);a[k]=1;repeat(10)@(negedge clk);
   b[k]=0;repeat(10)@(negedge clk);a[k]=0;repeat(10)@(negedge clk);end
 endtask
 integer i;
 initial begin
   force dut.rst=1;repeat(8)@(negedge clk);force dut.rst=0;
   force dut.core_state=128'd0;
   for(i=1;i<=16;i=i+1)begin
     detent(3);
     if(dut.panel_state[49:46]!==((8+i)%16)||dut.panel_state[102:99]!==dut.panel_state[49:46])
       $fatal(1,"name and selection disagree after detent %0d",i);
   end
   detent(0);repeat(20)@(negedge clk);
   if(dut.panel.master!==65||dut.panel_panic!==0||dut.engine.record_counter!==0||dut.engine.halt_counter!==0)
     $fatal(1,"volume detent or switch isolation failed");
   $display("PASS 16 live part names without playing, master detent without record/halt");$finish;
 end
endmodule
