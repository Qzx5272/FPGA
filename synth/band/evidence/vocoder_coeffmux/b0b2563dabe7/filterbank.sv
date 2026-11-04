// Adapted from VOXOS, MIT; see ../upstream/LICENSE and ../PROVENANCE.json.
`timescale 1ns / 1ps
`default_nettype none

function [31:0] abs(input [31:0] x);
  abs = (x == 32'h80000000) ? 32'h7fffffff : (x[31] ? -x : x);
endfunction

module filterbank
  #(parameter COEFF_FILE="coeffs.mem", parameter N_FILTERS=16, parameter COEFF_WIDTH=32)
(
  input wire clk_in,
  input wire rst_in,
  input wire valid_in,
  input wire signed [31:0] carrier_sample_in,
  input wire signed [31:0] modulator_sample_in,
  output logic signed [31:0] carrier_out [N_FILTERS-1:0],
  output logic signed [31:0] envelope_out [N_FILTERS-1:0],
  output wire ready_out,
  output logic valid_out
);

  // first N_FILTERS rows of coefficients are for bandpass filters
  // last coefficent row is for lowpass filter
  // Gowin V1.9.12.03 misloads this table when readmemh targets a2D array.
  // Keep file order explicit:row*10+column. Vendor netlist test covers all170 words.
  logic signed [31:0] COEFFS [0:(N_FILTERS+1)*10-1];
  initial $readmemh(COEFF_FILE, COEFFS);
  // synthesis translate_off
  initial begin
    #1;
    for (integer k=0;k<(N_FILTERS+1)*10;k=k+1)
      if ($signed(COEFFS[k]) != $signed(COEFFS[k][COEFF_WIDTH-1:0]))
        $fatal(1,"Coefficient does not fit COEFF_WIDTH");
  end
  // synthesis translate_on

  logic signed [31:0] modulator_past_samples       [1:0];
  logic signed [31:0] modulator_past_intermediates [N_FILTERS-1:0] [1:0];
  logic signed [31:0] modulator_past_outputs       [N_FILTERS-1:0] [1:0];

  logic signed [31:0] envelope_past_intermediates  [N_FILTERS-1:0] [1:0];
  logic signed [31:0] envelope_past_outputs        [N_FILTERS-1:0] [1:0];

  // needs to hold the newest sample since carrier signal is valid a few cycles early
  logic signed [31:0] carrier_past_samples         [2:0]; 
  logic signed [31:0] carrier_past_intermediates   [N_FILTERS-1:0] [1:0];
  logic signed [31:0] carrier_past_outputs         [N_FILTERS-1:0] [1:0];

  typedef enum { WAITING, MODULATOR, ENVELOPE, CARRIER } state_t;
  state_t state;
  assign ready_out = !rst_in && (state == WAITING);

  // generate N_FILTERS double-biquads for each band that do the modulator filtering, then
  // envelope detection, then carrier filtering

  // current inputs/outputs for the N_FILTERS double biquads
  wire signed [31:0] coeffs [N_FILTERS-1:0] [9:0];
  logic signed [31:0] x_n    [N_FILTERS-1:0];
  logic signed [31:0] x_n1   [N_FILTERS-1:0];
  logic signed [31:0] x_n2   [N_FILTERS-1:0];
  logic signed [31:0] i_n1   [N_FILTERS-1:0];
  logic signed [31:0] i_n2   [N_FILTERS-1:0];
  logic signed [31:0] y_n1   [N_FILTERS-1:0];
  logic signed [31:0] y_n2   [N_FILTERS-1:0];
  logic signed [31:0] i_n    [N_FILTERS-1:0];
  logic signed [31:0] y_n    [N_FILTERS-1:0];
  logic filters_valid_in;
  logic [N_FILTERS-1:0] filters_valid_out;

  generate
    for (genvar i = 0; i < N_FILTERS; i++) begin
      for (genvar c=0;c<10;c++) begin : coefficient_select
        assign coeffs[i][c] = (state == ENVELOPE) ? COEFFS[N_FILTERS*10+c] : COEFFS[i*10+c];
      end
      double_biquad #(.COEFF_WIDTH(COEFF_WIDTH)) bq(
        .clk_in(clk_in),
        .rst_in(rst_in),
        .valid_in(filters_valid_in),
        .b0_0(coeffs[i][0]),
        .b1_0(coeffs[i][1]),
        .b2_0(coeffs[i][2]),
        .a1_0(coeffs[i][3]),
        .a2_0(coeffs[i][4]),
        .b0_1(coeffs[i][5]),
        .b1_1(coeffs[i][6]),
        .b2_1(coeffs[i][7]),
        .a1_1(coeffs[i][8]),
        .a2_1(coeffs[i][9]),
        .x_n(x_n[i]),
        .x_n1(x_n1[i]),
        .x_n2(x_n2[i]),
        .i_n1(i_n1[i]),
        .i_n2(i_n2[i]),
        .y_n1(y_n1[i]),
        .y_n2(y_n2[i]),
        .i_n(i_n[i]),
        .y_n(y_n[i]),
        .valid_out(filters_valid_out[i])
      );
    end
  endgenerate

  always_ff @(posedge clk_in) begin
    if (rst_in) begin
      state <= WAITING;
      valid_out <= 0;
      filters_valid_in <= 0;
      for (int j=0;j<N_FILTERS;j++) begin
        x_n[j]<=0; x_n1[j]<=0; x_n2[j]<=0;
        i_n1[j]<=0; i_n2[j]<=0; y_n1[j]<=0; y_n2[j]<=0;
      end

      for (int i = 0; i < 2; i++) begin
        modulator_past_samples[i] <= 0;
        carrier_past_samples[i] <= 0;
        for (int j = 0; j < N_FILTERS; j++) begin
          modulator_past_intermediates[j][i] <= 0;
          modulator_past_outputs[j][i] <= 0;
          envelope_past_intermediates[j][i] <= 0;
          envelope_past_outputs[j][i] <= 0;
          carrier_past_intermediates[j][i] <= 0;
          carrier_past_outputs[j][i] <= 0;
          envelope_out[j] <= 0;
          carrier_out[j] <= 0;
        end
      end
      carrier_past_samples[2] <= 0;
    end else begin
      case (state)
        WAITING: begin
          valid_out <= 0;
          if (valid_in) begin
            state <= MODULATOR;
            
            // set inputs to filter modulator signal
            for (int i = 0; i < N_FILTERS; i++) begin
              // all filters receive the same modulator input
              x_n[i] <= modulator_sample_in;
              x_n1[i] <= modulator_past_samples[0];
              x_n2[i] <= modulator_past_samples[1];
              // intermediates and outputs vary by filter
              i_n1[i] <= modulator_past_intermediates[i][0];
              i_n2[i] <= modulator_past_intermediates[i][1];
              y_n1[i] <= modulator_past_outputs[i][0];
              y_n2[i] <= modulator_past_outputs[i][1];
            end
            filters_valid_in <= 1;

            // update all past sample values for modulator and carrier
            modulator_past_samples[0] <= modulator_sample_in;
            modulator_past_samples[1] <= modulator_past_samples[0];

            carrier_past_samples[0] <= carrier_sample_in;
            carrier_past_samples[1] <= carrier_past_samples[0];
            carrier_past_samples[2] <= carrier_past_samples[1];
          end
        end
        MODULATOR: begin
          if (&filters_valid_out) begin
            for (int i = 0; i < N_FILTERS; i++) begin
              // set inputs for envelope detector
              x_n[i] <= abs(y_n[i]);
              x_n1[i] <= abs(modulator_past_outputs[i][0]);
              x_n2[i] <= abs(modulator_past_outputs[i][1]);
              i_n1[i] <= envelope_past_intermediates[i][0];
              i_n2[i] <= envelope_past_intermediates[i][1];
              y_n1[i] <= envelope_past_outputs[i][0];
              y_n2[i] <= envelope_past_outputs[i][1];

              // filtered results already available since combinational
              // update all past intermediate/output values for modulator
              modulator_past_intermediates[i][0] <= i_n[i];
              modulator_past_intermediates[i][1] <= modulator_past_intermediates[i][0];
              modulator_past_outputs[i][0] <= y_n[i];
              modulator_past_outputs[i][1] <= modulator_past_outputs[i][0];
            end
            filters_valid_in <= 1;
            state <= ENVELOPE;
          end else filters_valid_in <= 0;
        end
        ENVELOPE: begin
          if (&filters_valid_out) begin
            for (int i = 0; i < N_FILTERS; i++) begin
              // set inputs to filter carrier signal
              x_n[i] <= carrier_past_samples[0];
              x_n1[i] <= carrier_past_samples[1];
              x_n2[i] <= carrier_past_samples[2];
              i_n1[i] <= carrier_past_intermediates[i][0];
              i_n2[i] <= carrier_past_intermediates[i][1];
              y_n1[i] <= carrier_past_outputs[i][0];
              y_n2[i] <= carrier_past_outputs[i][1];
              
              // update past results
              envelope_past_intermediates[i][0] <= i_n[i];
              envelope_past_intermediates[i][1] <= envelope_past_intermediates[i][0];
              envelope_past_outputs[i][0] <= y_n[i];
              envelope_past_outputs[i][1] <= envelope_past_outputs[i][0];

              envelope_out[i] <= y_n[i];
            end
            filters_valid_in <= 1;
            state <= CARRIER;
          end else filters_valid_in <= 0;
        end
        CARRIER: begin
          if (&filters_valid_out) begin
            for (int i = 0; i < N_FILTERS; i++) begin
              carrier_past_intermediates[i][0] <= i_n[i];
              carrier_past_intermediates[i][1] <= carrier_past_intermediates[i][0];
              carrier_past_outputs[i][0] <= y_n[i];
              carrier_past_outputs[i][1] <= carrier_past_outputs[i][0];

              carrier_out[i] <= y_n[i];
            end
            valid_out <= 1;
            state <= WAITING;
          end else filters_valid_in <= 0;
        end
      endcase
    end
  end 

endmodule

`default_nettype wire
