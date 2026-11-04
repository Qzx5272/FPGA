`timescale 1ns/1ps
module tb_i2s24_rx;
 reg bck=0;always #5 bck=~bck;
 reg rst=1,ws=0,sd=0,frame_ready=1;
 wire [47:0] frame_data;wire frame_valid;wire [31:0] framing_errors,overruns;
 i2s24_rx dut(.*);
 integer i,received=0;reg [47:0] expected;
 reg checking=0;
 always @(posedge bck)begin
  #1;
  if(checking&&frame_valid)begin
   if(frame_data!==expected)$fatal(1,"stereo mismatch got %h expected %h",frame_data,expected);
   received=received+1;
  end
 end
 task bit_tick;input channel,data;
 begin @(negedge bck);ws=channel;sd=data;@(posedge bck);#2;end endtask
 task word;input channel;input [23:0] data;input integer length;integer j;
 begin
  bit_tick(channel,1'b1); // delayed bit belongs to prior word; must be ignored
  for(j=1;j<length;j=j+1)bit_tick(channel,j<=24?data[24-j]:1'b1);
 end endtask
 initial begin
  repeat(3)@(negedge bck);rst=0;
  // Startup in the middle of left: discard until a complete left boundary.
  word(1,24'h123456,32);
  for(i=0;i<500;i=i+1)begin
   case(i%3)
    0:expected=48'h8000007fffff;
    1:expected=48'hffffff000001;
    2:expected={$random,$random};
   endcase
   word(0,expected[47:24],32);word(1,expected[23:0],32);
   checking=1;bit_tick(0,1);checking=0;
   // Complete this extra left word then right; accepted but not scored.
   repeat(31)bit_tick(0,0);word(1,24'd0,32);
  end
  if(received!=500||framing_errors||overruns)$fatal(1,"normal frame counts");
  // Reset midway through a word: no partial stereo frame may escape.
  bit_tick(0,1);repeat(12)bit_tick(0,1);
  @(negedge bck);rst=1;#1;if(frame_valid||frame_data)$fatal(1,"async reset");
  @(negedge bck);rst=0;
  word(1,24'h999999,32);word(0,24'h123456,32);word(1,24'habcdef,32);
  expected=48'h123456abcdef;checking=1;bit_tick(0,0);checking=0;
  // Finish this left short: should reject the entire pair.
  repeat(10)bit_tick(0,1);word(1,24'h654321,32);bit_tick(0,0);
  if(frame_valid||framing_errors!=1)$fatal(1,"short slot not rejected");
  repeat(31)bit_tick(0,0);word(1,24'd0,32);bit_tick(0,0);
  // Hold output under backpressure and ensure one newer frame is discarded.
  frame_ready=0;expected=frame_data;
  repeat(31)bit_tick(0,1);word(1,24'h123123,32);bit_tick(0,0);
  if(!frame_valid||frame_data!==expected||overruns!=1)$fatal(1,"backpressure overwrite");
  frame_ready=1;repeat(40)bit_tick(0,0);
  if(frame_valid||framing_errors!=2)$fatal(1,"long/stuck slot not rejected");
  word(1,24'd0,32);word(0,24'h800001,32);word(1,24'h7ffffe,32);
  expected=48'h8000017ffffe;checking=1;bit_tick(0,0);checking=0;
  $display("PASS RX:500 random/extreme stereo pairs, MSB delay, nonzero padding ignored, mid-word reset, short/long frames discarded, resync and backpressure exact");$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
