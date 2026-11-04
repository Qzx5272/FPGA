`timescale 1ns/1ps
// Monophonic, band-limited 64-harmonic saw carrier at48kHz.
// Reuses the measured interpolated sine kernel; no sampled audio playback.
// gate=0 releases the previous note/velocity. Legato preserves phase.
module vocoder_carrier(
 input wire clk,rst,panic,frame_valid,gate,
 input wire [6:0] note,velocity,
 output wire ready,
 output reg valid_out,output reg signed [23:0] sample_out,
 output reg [31:0] dropped_frames
);
 `include "midi_increment.vh"
 reg [2:0] state;
 reg [31:0] phase,held_phase,increment,held_increment;
 reg [15:0] envelope,held_envelope;
 reg [6:0] last_velocity,held_velocity,issued,received;
 reg signed [40:0] sum;
 reg request,product_valid,product_last;
 reg [31:0] sine_phase;
 wire sine_valid;wire signed [17:0] sine_sample;
 reg signed [34:0] product;
 reg signed [31:0] wave;
 reg signed [48:0] envelope_product;
 reg signed [56:0] velocity_product;
 wire signed [56:0] final_sample=velocity_product>>>23;
 wire [6:0] harmonic=issued+1'b1;
 wire [38:0] received_frequency=held_increment*(received+7'd1);
 wire [16:0] attack={1'b0,envelope}+17'd1024;
 wire [15:0] next_envelope=gate ? (attack>65535?16'd65535:attack[15:0]) : (envelope>512?envelope-16'd512:16'd0);
 wire [31:0] next_increment=gate?midi_increment(note):increment;
 assign ready=!rst&&!panic&&state==0;
 // Static case ROM, generated exact integer reciprocals, avoids a divider.
 function [15:0] coefficient(input [6:0] h);
  begin case(h)
`include "carrier_weights.vh"
   default:coefficient=0;
  endcase end
 endfunction
 hq_sine_quarter osc(clk,rst||panic,request,sine_phase,sine_valid,sine_sample);
 always @(posedge clk)begin
  if(rst||panic)begin
   state<=0;phase<=0;held_phase<=0;increment<=0;held_increment<=0;envelope<=0;held_envelope<=0;
   last_velocity<=0;held_velocity<=0;issued<=0;received<=0;sum<=0;
   request<=0;product_valid<=0;product_last<=0;product<=0;sine_phase<=0;
   wave<=0;envelope_product<=0;velocity_product<=0;valid_out<=0;sample_out<=0;dropped_frames<=0;
  end else begin
   request<=0;valid_out<=0;product_valid<=0;
   if(frame_valid&&!ready&&dropped_frames!=32'hffffffff)dropped_frames<=dropped_frames+1'b1;
   case(state)
    0:if(frame_valid)begin
     held_phase<=phase;held_increment<=next_increment;increment<=next_increment;phase<=phase+next_increment;
     envelope<=next_envelope;held_envelope<=next_envelope;
     if(gate)last_velocity<=velocity;
     held_velocity<=gate?velocity:last_velocity;issued<=0;received<=0;sum<=0;state<=1;
    end
    1:begin
     if(issued<64)begin
      sine_phase<=held_phase*harmonic;request<=1;issued<=issued+1'b1;
     end
     if(sine_valid)begin
      // Any partial at or above Nyquist is exactly suppressed.
      product<=sine_sample*$signed({1'b0,received_frequency<39'h0080000000 ? coefficient(received+7'd1):16'd0});
      product_valid<=1;product_last<=received==63;received<=received+1'b1;
     end
     if(product_valid)begin
      sum<=sum+product;
      if(product_last)begin wave<=(sum+product)>>>11;state<=2;end
     end
    end
    2:begin envelope_product<=wave*$signed({1'b0,held_envelope});state<=3;end
    3:begin velocity_product<=envelope_product*$signed({1'b0,held_velocity});state<=4;end
    4:begin
     sample_out<=final_sample>8388607?24'sh7fffff:final_sample < -8388608?24'sh800000:final_sample[23:0];
     valid_out<=1;state<=0;
    end
   endcase
  end
 end
endmodule
