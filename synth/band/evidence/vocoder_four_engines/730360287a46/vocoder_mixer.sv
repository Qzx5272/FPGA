`timescale 1ns/1ps
// Original Starcluster mixer. 16 signed carriers x nonnegative envelopes.
// Full 68-bit accumulation avoids overflow of sixteen 32x32 products.
module vocoder_mixer (
 input wire clk_in, rst_in, valid_in,
 input wire signed [31:0] carrier_in[15:0], envelope_in[15:0],
 output wire ready_out,
 output reg valid_out,
 output reg signed [23:0] sample_out,
 output reg [31:0] clip_count
);
 reg busy, phase;
 reg signed [63:0] product_reg;
 reg [3:0] index;
 reg signed [31:0] carrier[15:0], envelope[15:0];
 reg signed [67:0] sum;
 wire signed [63:0] product = carrier[index] * envelope[index];
 wire signed [67:0] total = sum + {{4{product_reg[63]}},product_reg};
 // Q23 input normalization, unity per-band gain. Final output saturates.
 wire signed [67:0] scaled = total >>> 23;
 assign ready_out = !rst_in && !busy;
 integer j;
 always @(posedge clk_in) begin
  if(rst_in) begin
   busy<=0;phase<=0;product_reg<=0;index<=0;sum<=0;valid_out<=0;sample_out<=0;clip_count<=0;
   for(j=0;j<16;j=j+1)begin carrier[j]<=0;envelope[j]<=0;end
  end else begin
   valid_out<=0;
   if(!busy)begin
    if(valid_in)begin
     for(j=0;j<16;j=j+1)begin
      carrier[j]<=carrier_in[j];
      // Rectified lowpass ringing must not reverse the carrier phase.
      envelope[j]<=envelope_in[j][31] ? 32'sd0 : envelope_in[j];
     end
     index<=0;sum<=0;busy<=1;phase<=0;
    end
   end else if(!phase)begin
    product_reg<=product;phase<=1;
   end else begin
    phase<=0;
    if(index==15)begin
     busy<=0;valid_out<=1;
     if(scaled>8388607)begin
      sample_out<=24'sh7fffff;
      if(clip_count!=32'hffffffff)clip_count<=clip_count+1'b1;
     end else if(scaled < -8388608)begin
      sample_out<=24'sh800000;
      if(clip_count!=32'hffffffff)clip_count<=clip_count+1'b1;
     end else sample_out<=scaled[23:0];
    end else begin sum<=total;index<=index+1'b1;end
   end
  end
 end
endmodule
