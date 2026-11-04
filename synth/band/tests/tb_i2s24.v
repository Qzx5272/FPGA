`timescale 1ns/1ps
module tb_i2s24;
 reg clk_audio=0;always #20.345052 clk_audio=~clk_audio;
 reg rst=1;reg [47:0] frame_data=0;reg frame_valid=1;
 wire frame_pop,frame_request_toggle,bck,ws,sd;wire [31:0] underruns;
 i2s24_tx dut(.*);
 reg [47:0] expect_frame;reg [23:0] received=0;
 integer checked=0,frames=0,misses=0,rxslot=-1;
 reg started=0;reg previous_ws=0;reg reset_done=0;
 // Drive well away from serializer's falling BCK edge.
 always @(negedge clk_audio)begin
   if(!rst && dut.div==7 && dut.slot==0)begin
     frame_valid=(frames%17!=7);
     case(frames%11)
       0:frame_data=48'h8000007fffff;
       1:frame_data=48'hffffff000001;
       default:frame_data={$random,$random};
     endcase
     expect_frame=frame_valid ? frame_data:0;
     if(!frame_valid)misses=misses+1;
     frames=frames+1;started=1;rxslot=-1;
   end
 end
 always @(posedge bck)begin
   if(!rst && started)begin
     rxslot=rxslot+1;
     if(ws!==(rxslot>=32))begin $display("WS misalignment %0d",rxslot);$fatal;end
     if((rxslot%32)>=1 && (rxslot%32)<=24)received={received[22:0],sd};
     else if(sd!==0)begin $display("Nonzero padding");$fatal;end
     if(rxslot==24 || rxslot==56)begin
       if(received!==(rxslot==24 ? expect_frame[47:24]:expect_frame[23:0]))begin
         $display("FAIL frame %0d slot %0d got %h expected %h",frames,rxslot,received,expect_frame);$fatal;
       end
       checked=checked+1;
     end
     if(frames==500 && rxslot==63)begin
       if(underruns!=misses)$fatal;
       if(!reset_done)$fatal;
       $display("PASS I2S: %0d post-reset stereo frames, %0d exact channel words, %0d zero-filled underruns; mid-word reset, WS one-bit delay and padding checked",frames,checked,misses);
       $finish;
     end
   end
 end
 initial begin repeat(6)@(negedge clk_audio);rst=0;end
 initial begin
   wait(frames==250 && rxslot==13);
   @(negedge clk_audio);#1;rst=1;started=0;
   repeat(7)@(negedge clk_audio);#1;
   if(bck!==0 || ws!==0 || sd!==0 || underruns!==0 || frame_request_toggle!==0)$fatal(1,"reset state");
   frames=0;checked=0;misses=0;rxslot=-1;reset_done=1;rst=0;
 end
 initial begin #20000000;$fatal(1,"timeout");end
endmodule
