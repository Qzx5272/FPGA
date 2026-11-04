// PCM transport for singer integration; no physical pin assignment.
// Latest complete left-channel frame is sampled at the band's sample_tick.
// This is NOT an asynchronous sample-rate converter: repeated/skipped counts
// expose input/output rate mismatch, which requires shared clocks or an ASRC.
module microphone_capture #(parameter TIMEOUT_CYCLES=5000000)(
 input wire core_clk,rst,panic,bck,ws,sd,sample_tick,
 output wire signed [23:0] microphone_sample,output reg input_stale,
 output reg [31:0] received_frames,repeated_frames,skipped_frames,timeouts,
 output wire [31:0] framing_errors_bck,overruns_bck
);
 wire frame_valid;wire[47:0]frame_data;reg flush;
 reg [31:0]idle_cycles;reg fresh;
 reg signed[23:0]latest,held;
 i2s_input_bridge transport(bck,ws,sd,core_clk,rst||panic||flush,
  frame_valid,frame_valid,frame_data,framing_errors_bck,overruns_bck);
 assign microphone_sample=rst||panic||input_stale?24'sd0:held;
 always @(posedge core_clk)begin
  if(rst||panic)begin
   input_stale<=1;flush<=0;idle_cycles<=0;fresh<=0;latest<=0;held<=0;
   received_frames<=0;repeated_frames<=0;skipped_frames<=0;timeouts<=0;
  end else begin
   flush<=0;
   if(frame_valid)begin
    latest<=frame_data[47:24];fresh<=1;input_stale<=0;idle_cycles<=0;
    if(received_frames!=32'hffffffff)received_frames<=received_frames+1'b1;
    if(fresh&&!sample_tick&&skipped_frames!=32'hffffffff)skipped_frames<=skipped_frames+1'b1;
   end else if(!input_stale)begin
    if(idle_cycles>=TIMEOUT_CYCLES-1)begin
     input_stale<=1;flush<=1;fresh<=0;latest<=0;held<=0;
     if(timeouts!=32'hffffffff)timeouts<=timeouts+1'b1;
    end else idle_cycles<=idle_cycles+1'b1;
   end
   if(sample_tick)begin
    held<=frame_valid?frame_data[47:24]:latest;fresh<=0;
    if(!fresh&&!frame_valid&&!input_stale&&repeated_frames!=32'hffffffff)repeated_frames<=repeated_frames+1'b1;
   end
  end
 end
endmodule
