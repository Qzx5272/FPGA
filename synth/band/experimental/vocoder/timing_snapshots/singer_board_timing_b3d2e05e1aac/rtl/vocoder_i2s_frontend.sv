`timescale 1ns/1ps
// Optional microphone transport + vocoder, not a production pin assignment.
// Left I2S channel is the modulator. Carrier comes from a core-clock synth.
// STEREO_TEST_CARRIER=1 uses right channel only for deterministic loop tests.
module vocoder_i2s_frontend #(
 parameter COEFF_FILE="coeffs.mem", parameter TIMEOUT_CYCLES=5000000,
 parameter STEREO_TEST_CARRIER=0
)(
 input wire core_clk,rst,panic,input_bck,input_ws,input_sd,
 input wire signed [23:0] synth_carrier,
 output wire signed [23:0] sample_out,output wire sample_valid,
 output reg input_stale,
 output wire [31:0] clip_count,rejected_count,
 output wire [31:0] framing_errors_bck,overruns_bck
);
 wire reset_async=rst||panic;
 (* async_reg="true" *) reg [1:0] reset_sync;
 always @(posedge core_clk or posedge reset_async)
  if(reset_async)reset_sync<=3;else reset_sync<={reset_sync[0],1'b0};
 wire frame_valid,frame_pop,ready,raw_valid;
 wire [47:0] frame_data;
 wire signed [23:0] raw_sample;
 reg [31:0] idle_cycles;
 reg stale_pulse;
 i2s_input_bridge input_transport(input_bck,input_ws,input_sd,core_clk,reset_async,
  frame_pop,frame_valid,frame_data,framing_errors_bck,overruns_bck);
 assign frame_pop=frame_valid && ready && !input_stale;
 // Loss of BCK is detected in the independent core clock domain.
 always @(posedge core_clk)begin
  if(reset_sync[1])begin idle_cycles<=0;input_stale<=1;stale_pulse<=0;end
  else begin
   stale_pulse<=0;
   if(frame_valid)begin idle_cycles<=0;input_stale<=0;end
   else if(!input_stale)begin
    if(idle_cycles>=TIMEOUT_CYCLES-1)begin input_stale<=1;stale_pulse<=1;end
    else idle_cycles<=idle_cycles+1'b1;
   end
  end
 end
 vocoder_core #(.COEFF_FILE(COEFF_FILE)) core(
  .clk_in(core_clk),.rst_in(reset_sync[1]||input_stale),.valid_in(frame_pop),
  .carrier_sample_in(STEREO_TEST_CARRIER ? frame_data[23:0] : synth_carrier),
  .modulator_sample_in(frame_data[47:24]),.ready_out(ready),
  .valid_out(raw_valid),.sample_out(raw_sample),.clip_count(clip_count),.rejected_count(rejected_count));
 assign sample_out=input_stale||reset_sync[1] ? 24'sd0 : raw_sample;
 assign sample_valid=!reset_sync[1] && (stale_pulse||(!input_stale&&raw_valid));
endmodule
