`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1;
 always #20.344827586 clk=~clk;
 reg signed [23:0] txl=24'h812345,txr=24'h765432;
 wire bck,ws,sd,tick,valid;
 wire signed [23:0] mic;
 tri mic_wire;
 reg mic_drive=0,drive_enable=0;
 assign mic_wire=drive_enable ? mic_drive : 1'bz;
 pullup(mic_wire); // inactive right slot is deliberately NOT zero
 i2s_master_duplex dut(clk,rst,txl,txr,mic_wire,bck,ws,sd,tick,valid,mic);
 integer rx_count=0,tx_count=0,mic_slot=0,tx_slot=0,bit_count=0;
 reg mic_prev_ws=1,tx_prev_ws=0,tx_synced=0,saw_right=0;
 reg [23:0] expected_mic=24'h812345,word=0,left_word=0;
 reg [23:0] values[0:7];
 // Independent microphone pin model: one-bit I2S delay; left selected;
 // SD high impedance after 24 bits and throughout right; 70ns total delay.
 always @(negedge bck) if(!rst) begin
  #1;
  if(ws!=mic_prev_ws) begin mic_slot=0;mic_prev_ws=ws;end
  else mic_slot=mic_slot+1;
  if(!ws && mic_slot>=1 && mic_slot<=24) begin
   drive_enable<=#69 1;mic_drive<=#69 expected_mic[24-mic_slot];
  end else drive_enable<=#69 0;
 end
 always @(posedge bck) if(!rst) begin
  if(ws) saw_right=1;
  if(saw_right&&!ws&&tx_prev_ws) tx_synced=1;
  if(ws!=tx_prev_ws) begin
   if(tx_synced&&bit_count>0 && bit_count!=32) $fatal(1,"not 32 bits/channel %d",bit_count);
   tx_slot=0;bit_count=1;tx_prev_ws=ws;
  end else begin tx_slot=tx_slot+1;bit_count=bit_count+1;end
  if(tx_slot>=1&&tx_slot<=24) word={word[22:0],sd};
  else if(tx_synced&&sd!==0) $fatal(1,"nonzero padding");
  if(tx_synced&&tx_slot==24) begin
   if(!ws) left_word=word;
   else begin
    if(left_word!==txl || word!==txr) $fatal(1,"TX mismatch %h %h",left_word,word);
    tx_count=tx_count+1;
   end
  end
 end
 always @(negedge clk) if(valid&&!rst) begin
  if(mic!==expected_mic) $fatal(1,"RX expected %h got %h",expected_mic,mic);
  rx_count=rx_count+1;
  expected_mic=values[rx_count%8];
 end
 initial begin
  values[0]=24'h812345;values[1]=24'h7fffff;values[2]=24'h800000;
  values[3]=24'h000001;values[4]=24'hffffff;values[5]=0;
  values[6]=24'h555555;values[7]=24'haaaaaa;
  repeat(8) @(negedge clk);rst=0;
  wait(rx_count>=64&&tx_count>=64);
  $display("PASS duplex 64 stereo frames, 24-bit signed extremes, I2S delay, 64 clocks/frame, tri-state microphone, 70ns pad delay");
  $finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
