// Optional external DAC transport, not wired into the PT8211 board candidate.
// audio_clk MUST be a verified 24.576 MHz clock: 48 kHz, 32-bit stereo slots, 24 data bits.
// Reuses research i2s24_tx; new CDC must be separately constrained and measured on hardware.
module audio_i2s_bridge(
 input wire core_clk,audio_clk,rst,panic,
 input wire sample_valid,input wire signed [23:0] left,right,
 output wire sample_tick,bck,ws,sd,
 output reg [31:0] dropped_frames,output wire [31:0] underruns_audio_domain
);
 wire reset_async=rst||panic;
 (* async_reg="true" *) reg [1:0] core_reset,audio_reset;
 always @(posedge core_clk or posedge reset_async)if(reset_async)core_reset<=3;else core_reset<={core_reset[0],1'b0};
 always @(posedge audio_clk or posedge reset_async)if(reset_async)audio_reset<=3;else audio_reset<={audio_reset[0],1'b0};
 wire ready,valid,pop,request;wire [47:0] frame;
 audio_cdc_fifo fifo(core_clk,core_reset[1],sample_valid,{left,right},ready,
  audio_clk,audio_reset[1],pop,valid,frame);
 i2s24_tx serializer(audio_clk,audio_reset[1],frame,valid,pop,request,bck,ws,sd,underruns_audio_domain);
 (* async_reg="true" *) reg request1,request2;reg previous;
 assign sample_tick=request2^previous;
 always @(posedge core_clk or posedge reset_async)begin
  if(reset_async)begin request1<=0;request2<=0;previous<=0;dropped_frames<=0;end
  else if(core_reset[1])begin request1<=0;request2<=0;previous<=0;dropped_frames<=0;end
  else begin
   request1<=request;request2<=request1;previous<=request2;
   if(sample_valid&&!ready&&dropped_frames!=32'hffffffff)dropped_frames<=dropped_frames+1'b1;
  end
 end
endmodule
