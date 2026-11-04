// Research serializer. clk_audio=24.576MHz, BCK=3.072MHz, LRCK=48kHz.
// FIFO is FWFT and synchronous to clk_audio; CDC belongs outside this module.
// WS changes one BCK before MSB. Each channel has 32 bit slots / 24 data bits.
module i2s24_tx(input wire clk_audio,rst,
    input wire [47:0] frame_data,input wire frame_valid,
    output reg frame_pop,output reg frame_request_toggle,
    output reg bck,ws,sd,output reg [31:0] underruns);
 reg [2:0] div;
 reg [5:0] slot;
 reg [47:0] current_frame;
 wire [4:0] channel_slot=slot[4:0];
 always @(posedge clk_audio)begin
   frame_pop<=0;
   if(rst)begin
     div<=0;slot<=0;current_frame<=0;bck<=0;ws<=0;sd<=0;
     underruns<=0;frame_request_toggle<=0;frame_pop<=0;
   end else begin
     div<=div+1'b1;
     if(div==3)bck<=1;
     if(div==7)begin
       bck<=0;slot<=slot+1'b1;ws<=slot[5];
       if(slot==0)begin
         current_frame<=frame_valid ? frame_data:48'd0;
         frame_pop<=frame_valid;
         frame_request_toggle<=~frame_request_toggle;
         if(!frame_valid && underruns!=32'hffffffff)underruns<=underruns+1'b1;
       end
       if(channel_slot>=1 && channel_slot<=24)
         sd<=slot[5] ? current_frame[24-channel_slot] : current_frame[48-channel_slot];
       else sd<=0;
     end
   end
 end
endmodule
