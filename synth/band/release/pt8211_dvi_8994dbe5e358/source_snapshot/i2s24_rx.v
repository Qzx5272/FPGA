// Fixed profile: I2S, two 32-bit slots, 24-bit two's-complement audio.
// All outputs and ready are in the incoming BCK domain. Add a dual-clock FIFO
// before the 50MHz engine; rst deassertion must be synchronized to BCK.
// WS changes one rising BCK before MSB. Output only complete validated pairs.
module i2s24_rx(input wire bck,rst,ws,sd,input wire frame_ready,
 output reg [47:0] frame_data,output reg frame_valid,
 output reg [31:0] framing_errors,overruns);
 reg previous_ws,synced,left_valid;
 reg [5:0] count;
 reg [23:0] word_shift,left_word;
 always @(posedge bck or posedge rst)begin
  if(rst)begin
   previous_ws<=0;synced<=0;left_valid<=0;count<=0;
   word_shift<=0;left_word<=0;frame_data<=0;frame_valid<=0;
   framing_errors<=0;overruns<=0;
  end else begin
   previous_ws<=ws;
   if(frame_ready)frame_valid<=0;
   if(ws!=previous_ws)begin
    count<=0;word_shift<=0;
    if(!synced)begin
     if(!ws)synced<=1;
     left_valid<=0;
    end else if(count!=31)begin
     left_valid<=0;
     if(framing_errors!=32'hffffffff)framing_errors<=framing_errors+1'b1;
    end else if(ws)begin left_word<=word_shift;left_valid<=1;end
    else begin
     left_valid<=0;
     if(left_valid)begin
      if(!frame_valid||frame_ready)begin frame_data<={left_word,word_shift};frame_valid<=1;end
      else if(overruns!=32'hffffffff)overruns<=overruns+1'b1;
     end
    end
   end else if(synced)begin
    if(count==31)begin
     synced<=0;left_valid<=0;
     if(framing_errors!=32'hffffffff)framing_errors<=framing_errors+1'b1;
    end else begin
     count<=count+1'b1;
     if(count<24)word_shift<={word_shift[22:0],sd};
    end
   end
  end
 end
endmodule
