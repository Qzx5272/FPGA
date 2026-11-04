`timescale 1ns/1ps
// Isolated 48kHz vocoder prototype; no board pin or production integration.
module vocoder_core #(parameter COEFF_FILE="coeffs.mem") (
 input wire clk_in,rst_in,valid_in,
 input wire signed [23:0] carrier_sample_in,modulator_sample_in,
 output wire ready_out,valid_out,
 output wire signed [23:0] sample_out,
 output wire [31:0] clip_count,
 output reg [31:0] rejected_count
);
 wire signed [31:0] carrier[15:0], envelope[15:0];
 wire bank_ready,bank_valid,mix_ready;
 reg active;
 assign ready_out = !rst_in && !active && bank_ready && mix_ready;
 // Supplied Q20 coefficients fit signed22 exactly; host build guard enforces it.
 // Samples and arithmetic rounding retain their full original precision.
 filterbank #(.COEFF_FILE(COEFF_FILE),.COEFF_WIDTH(22)) bank (
  .clk_in(clk_in),.rst_in(rst_in),.valid_in(valid_in && ready_out),
  .carrier_sample_in({{8{carrier_sample_in[23]}},carrier_sample_in}),
  .modulator_sample_in({{8{modulator_sample_in[23]}},modulator_sample_in}),
  .carrier_out(carrier),.envelope_out(envelope),
  .ready_out(bank_ready),.valid_out(bank_valid));
 vocoder_mixer mixer(.clk_in(clk_in),.rst_in(rst_in),.valid_in(bank_valid),
  .carrier_in(carrier),.envelope_in(envelope),.ready_out(mix_ready),
  .valid_out(valid_out),.sample_out(sample_out),.clip_count(clip_count));
 always @(posedge clk_in)begin
  if(rst_in)begin active<=0;rejected_count<=0;end
  else begin
   if(valid_in && ready_out) active<=1;
   if(valid_out) active<=0;
   if(valid_in && !ready_out && rejected_count!=32'hffffffff)
    rejected_count<=rejected_count+1'b1;
  end
 end
endmodule
