// Optional input transport, not connected to any released board pins.
// Counters ending _bck remain in the input domain; do not sample them as an
// unsynchronized multibit bus in a host interface. Audio crosses via Gray FIFO.
module i2s_input_bridge(input wire bck,ws,sd,core_clk,rst,
 input wire frame_pop,output wire frame_valid,output wire [47:0] frame_data,
 output wire [31:0] framing_errors_bck,overruns_bck);
 (* async_reg="true" *) reg [1:0] input_reset,core_reset;
 always @(posedge bck or posedge rst)
  if(rst)input_reset<=2'b11;else input_reset<={input_reset[0],1'b0};
 always @(posedge core_clk or posedge rst)
  if(rst)core_reset<=2'b11;else core_reset<={core_reset[0],1'b0};
 wire valid,ready;wire [47:0] data;
 i2s24_rx receiver(bck,input_reset[1],ws,sd,ready,data,valid,framing_errors_bck,overruns_bck);
 audio_cdc_fifo fifo(bck,input_reset[1],valid,data,ready,
  core_clk,core_reset[1],frame_pop,frame_valid,frame_data);
endmodule
