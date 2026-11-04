// One clock domain. 24 data bits in each 32-bit slot, Philips I2S delay.
// audio_clk / 8 = BCLK; audio_clk / 512 = LRCK.
// rx_sd is the INMP441 data line; L/R must be low (left slot).
module i2s_master_duplex(
 input wire audio_clk, rst,
 input wire signed [23:0] tx_left, tx_right,
 input wire rx_sd,
 output reg bck, ws, tx_sd,
 output reg frame_tick, rx_valid,
 output reg signed [23:0] rx_left
);
 reg [2:0] div;
 reg [5:0] slot;
 reg [47:0] frame;
 reg [23:0] rx_shift;
 // Source-synchronous external data is allowed to settle for half a bit.
 // Two register stages; consume at div=5, corresponding to pad at div=3.
 (* ASYNC_REG="TRUE" *) reg rx_meta, rx_sync;
 wire [5:0] active_slot = slot - 6'd1;
 always @(posedge audio_clk) begin
  if(rst) begin
   div<=0;slot<=0;frame<=0;rx_shift<=0;rx_left<=0;
   bck<=0;ws<=0;tx_sd<=0;frame_tick<=0;rx_valid<=0;
   rx_meta<=0;rx_sync<=0;
  end else begin
   rx_meta<=rx_sd;rx_sync<=rx_meta;
   frame_tick<=0;rx_valid<=0;div<=div+1'b1;
   if(div==3) bck<=1;
   if(div==7) begin
    bck<=0;slot<=slot+1'b1;ws<=slot[5];
    if(slot==0) begin frame<={tx_left,tx_right};frame_tick<=1;end
    if(slot[4:0]>=1 && slot[4:0]<=24)
     tx_sd<=slot[5] ? frame[24-slot[4:0]] : frame[48-slot[4:0]];
    else tx_sd<=0;
   end
   if(div==5 && !active_slot[5]) begin
    if(active_slot[4:0]==0) rx_shift<=0;
    else if(active_slot[4:0]<=24) begin
     rx_shift<={rx_shift[22:0],rx_sync};
     if(active_slot[4:0]==24) begin
      rx_left<={rx_shift[22:0],rx_sync};rx_valid<=1;
     end
    end
   end
  end
 end
endmodule
