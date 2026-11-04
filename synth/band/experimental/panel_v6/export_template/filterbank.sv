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
  logic signed [31:0] coeffs [0:N_FILTERS*10-1];
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

  // Experimental: four arithmetic engines retain all sixteen band histories.
  localparam GROUPS=N_FILTERS/4;
  reg [31:0] group_index;
  reg engine_launch,engine_busy;
  wire [3:0] engine_done;
  wire signed [31:0] engine_i[0:3],engine_y[0:3];
  initial begin if(N_FILTERS!=16)$fatal(1,"four-engine candidate requires16 bands");end
  generate
  if(1)begin:shared_engine_0
    double_biquad #(.COEFF_WIDTH(COEFF_WIDTH)) bq(
      .clk_in(clk_in),
      .rst_in(rst_in),
      .valid_in(engine_launch),
      .b0_0((group_index==0 ? coeffs[0] : group_index==1 ? coeffs[40] : group_index==2 ? coeffs[80] : coeffs[120])),
      .b1_0((group_index==0 ? coeffs[1] : group_index==1 ? coeffs[41] : group_index==2 ? coeffs[81] : coeffs[121])),
      .b2_0((group_index==0 ? coeffs[2] : group_index==1 ? coeffs[42] : group_index==2 ? coeffs[82] : coeffs[122])),
      .a1_0((group_index==0 ? coeffs[3] : group_index==1 ? coeffs[43] : group_index==2 ? coeffs[83] : coeffs[123])),
      .a2_0((group_index==0 ? coeffs[4] : group_index==1 ? coeffs[44] : group_index==2 ? coeffs[84] : coeffs[124])),
      .b0_1((group_index==0 ? coeffs[5] : group_index==1 ? coeffs[45] : group_index==2 ? coeffs[85] : coeffs[125])),
      .b1_1((group_index==0 ? coeffs[6] : group_index==1 ? coeffs[46] : group_index==2 ? coeffs[86] : coeffs[126])),
      .b2_1((group_index==0 ? coeffs[7] : group_index==1 ? coeffs[47] : group_index==2 ? coeffs[87] : coeffs[127])),
      .a1_1((group_index==0 ? coeffs[8] : group_index==1 ? coeffs[48] : group_index==2 ? coeffs[88] : coeffs[128])),
      .a2_1((group_index==0 ? coeffs[9] : group_index==1 ? coeffs[49] : group_index==2 ? coeffs[89] : coeffs[129])),
      .x_n((group_index==0 ? x_n[0] : group_index==1 ? x_n[4] : group_index==2 ? x_n[8] : x_n[12])),
      .x_n1((group_index==0 ? x_n1[0] : group_index==1 ? x_n1[4] : group_index==2 ? x_n1[8] : x_n1[12])),
      .x_n2((group_index==0 ? x_n2[0] : group_index==1 ? x_n2[4] : group_index==2 ? x_n2[8] : x_n2[12])),
      .i_n1((group_index==0 ? i_n1[0] : group_index==1 ? i_n1[4] : group_index==2 ? i_n1[8] : i_n1[12])),
      .i_n2((group_index==0 ? i_n2[0] : group_index==1 ? i_n2[4] : group_index==2 ? i_n2[8] : i_n2[12])),
      .y_n1((group_index==0 ? y_n1[0] : group_index==1 ? y_n1[4] : group_index==2 ? y_n1[8] : y_n1[12])),
      .y_n2((group_index==0 ? y_n2[0] : group_index==1 ? y_n2[4] : group_index==2 ? y_n2[8] : y_n2[12])),
      .i_n(engine_i[0]),
      .y_n(engine_y[0]),
      .valid_out(engine_done[0]));
  end
  if(1)begin:shared_engine_1
    double_biquad #(.COEFF_WIDTH(COEFF_WIDTH)) bq(
      .clk_in(clk_in),
      .rst_in(rst_in),
      .valid_in(engine_launch),
      .b0_0((group_index==0 ? coeffs[10] : group_index==1 ? coeffs[50] : group_index==2 ? coeffs[90] : coeffs[130])),
      .b1_0((group_index==0 ? coeffs[11] : group_index==1 ? coeffs[51] : group_index==2 ? coeffs[91] : coeffs[131])),
      .b2_0((group_index==0 ? coeffs[12] : group_index==1 ? coeffs[52] : group_index==2 ? coeffs[92] : coeffs[132])),
      .a1_0((group_index==0 ? coeffs[13] : group_index==1 ? coeffs[53] : group_index==2 ? coeffs[93] : coeffs[133])),
      .a2_0((group_index==0 ? coeffs[14] : group_index==1 ? coeffs[54] : group_index==2 ? coeffs[94] : coeffs[134])),
      .b0_1((group_index==0 ? coeffs[15] : group_index==1 ? coeffs[55] : group_index==2 ? coeffs[95] : coeffs[135])),
      .b1_1((group_index==0 ? coeffs[16] : group_index==1 ? coeffs[56] : group_index==2 ? coeffs[96] : coeffs[136])),
      .b2_1((group_index==0 ? coeffs[17] : group_index==1 ? coeffs[57] : group_index==2 ? coeffs[97] : coeffs[137])),
      .a1_1((group_index==0 ? coeffs[18] : group_index==1 ? coeffs[58] : group_index==2 ? coeffs[98] : coeffs[138])),
      .a2_1((group_index==0 ? coeffs[19] : group_index==1 ? coeffs[59] : group_index==2 ? coeffs[99] : coeffs[139])),
      .x_n((group_index==0 ? x_n[1] : group_index==1 ? x_n[5] : group_index==2 ? x_n[9] : x_n[13])),
      .x_n1((group_index==0 ? x_n1[1] : group_index==1 ? x_n1[5] : group_index==2 ? x_n1[9] : x_n1[13])),
      .x_n2((group_index==0 ? x_n2[1] : group_index==1 ? x_n2[5] : group_index==2 ? x_n2[9] : x_n2[13])),
      .i_n1((group_index==0 ? i_n1[1] : group_index==1 ? i_n1[5] : group_index==2 ? i_n1[9] : i_n1[13])),
      .i_n2((group_index==0 ? i_n2[1] : group_index==1 ? i_n2[5] : group_index==2 ? i_n2[9] : i_n2[13])),
      .y_n1((group_index==0 ? y_n1[1] : group_index==1 ? y_n1[5] : group_index==2 ? y_n1[9] : y_n1[13])),
      .y_n2((group_index==0 ? y_n2[1] : group_index==1 ? y_n2[5] : group_index==2 ? y_n2[9] : y_n2[13])),
      .i_n(engine_i[1]),
      .y_n(engine_y[1]),
      .valid_out(engine_done[1]));
  end
  if(1)begin:shared_engine_2
    double_biquad #(.COEFF_WIDTH(COEFF_WIDTH)) bq(
      .clk_in(clk_in),
      .rst_in(rst_in),
      .valid_in(engine_launch),
      .b0_0((group_index==0 ? coeffs[20] : group_index==1 ? coeffs[60] : group_index==2 ? coeffs[100] : coeffs[140])),
      .b1_0((group_index==0 ? coeffs[21] : group_index==1 ? coeffs[61] : group_index==2 ? coeffs[101] : coeffs[141])),
      .b2_0((group_index==0 ? coeffs[22] : group_index==1 ? coeffs[62] : group_index==2 ? coeffs[102] : coeffs[142])),
      .a1_0((group_index==0 ? coeffs[23] : group_index==1 ? coeffs[63] : group_index==2 ? coeffs[103] : coeffs[143])),
      .a2_0((group_index==0 ? coeffs[24] : group_index==1 ? coeffs[64] : group_index==2 ? coeffs[104] : coeffs[144])),
      .b0_1((group_index==0 ? coeffs[25] : group_index==1 ? coeffs[65] : group_index==2 ? coeffs[105] : coeffs[145])),
      .b1_1((group_index==0 ? coeffs[26] : group_index==1 ? coeffs[66] : group_index==2 ? coeffs[106] : coeffs[146])),
      .b2_1((group_index==0 ? coeffs[27] : group_index==1 ? coeffs[67] : group_index==2 ? coeffs[107] : coeffs[147])),
      .a1_1((group_index==0 ? coeffs[28] : group_index==1 ? coeffs[68] : group_index==2 ? coeffs[108] : coeffs[148])),
      .a2_1((group_index==0 ? coeffs[29] : group_index==1 ? coeffs[69] : group_index==2 ? coeffs[109] : coeffs[149])),
      .x_n((group_index==0 ? x_n[2] : group_index==1 ? x_n[6] : group_index==2 ? x_n[10] : x_n[14])),
      .x_n1((group_index==0 ? x_n1[2] : group_index==1 ? x_n1[6] : group_index==2 ? x_n1[10] : x_n1[14])),
      .x_n2((group_index==0 ? x_n2[2] : group_index==1 ? x_n2[6] : group_index==2 ? x_n2[10] : x_n2[14])),
      .i_n1((group_index==0 ? i_n1[2] : group_index==1 ? i_n1[6] : group_index==2 ? i_n1[10] : i_n1[14])),
      .i_n2((group_index==0 ? i_n2[2] : group_index==1 ? i_n2[6] : group_index==2 ? i_n2[10] : i_n2[14])),
      .y_n1((group_index==0 ? y_n1[2] : group_index==1 ? y_n1[6] : group_index==2 ? y_n1[10] : y_n1[14])),
      .y_n2((group_index==0 ? y_n2[2] : group_index==1 ? y_n2[6] : group_index==2 ? y_n2[10] : y_n2[14])),
      .i_n(engine_i[2]),
      .y_n(engine_y[2]),
      .valid_out(engine_done[2]));
  end
  if(1)begin:shared_engine_3
    double_biquad #(.COEFF_WIDTH(COEFF_WIDTH)) bq(
      .clk_in(clk_in),
      .rst_in(rst_in),
      .valid_in(engine_launch),
      .b0_0((group_index==0 ? coeffs[30] : group_index==1 ? coeffs[70] : group_index==2 ? coeffs[110] : coeffs[150])),
      .b1_0((group_index==0 ? coeffs[31] : group_index==1 ? coeffs[71] : group_index==2 ? coeffs[111] : coeffs[151])),
      .b2_0((group_index==0 ? coeffs[32] : group_index==1 ? coeffs[72] : group_index==2 ? coeffs[112] : coeffs[152])),
      .a1_0((group_index==0 ? coeffs[33] : group_index==1 ? coeffs[73] : group_index==2 ? coeffs[113] : coeffs[153])),
      .a2_0((group_index==0 ? coeffs[34] : group_index==1 ? coeffs[74] : group_index==2 ? coeffs[114] : coeffs[154])),
      .b0_1((group_index==0 ? coeffs[35] : group_index==1 ? coeffs[75] : group_index==2 ? coeffs[115] : coeffs[155])),
      .b1_1((group_index==0 ? coeffs[36] : group_index==1 ? coeffs[76] : group_index==2 ? coeffs[116] : coeffs[156])),
      .b2_1((group_index==0 ? coeffs[37] : group_index==1 ? coeffs[77] : group_index==2 ? coeffs[117] : coeffs[157])),
      .a1_1((group_index==0 ? coeffs[38] : group_index==1 ? coeffs[78] : group_index==2 ? coeffs[118] : coeffs[158])),
      .a2_1((group_index==0 ? coeffs[39] : group_index==1 ? coeffs[79] : group_index==2 ? coeffs[119] : coeffs[159])),
      .x_n((group_index==0 ? x_n[3] : group_index==1 ? x_n[7] : group_index==2 ? x_n[11] : x_n[15])),
      .x_n1((group_index==0 ? x_n1[3] : group_index==1 ? x_n1[7] : group_index==2 ? x_n1[11] : x_n1[15])),
      .x_n2((group_index==0 ? x_n2[3] : group_index==1 ? x_n2[7] : group_index==2 ? x_n2[11] : x_n2[15])),
      .i_n1((group_index==0 ? i_n1[3] : group_index==1 ? i_n1[7] : group_index==2 ? i_n1[11] : i_n1[15])),
      .i_n2((group_index==0 ? i_n2[3] : group_index==1 ? i_n2[7] : group_index==2 ? i_n2[11] : i_n2[15])),
      .y_n1((group_index==0 ? y_n1[3] : group_index==1 ? y_n1[7] : group_index==2 ? y_n1[11] : y_n1[15])),
      .y_n2((group_index==0 ? y_n2[3] : group_index==1 ? y_n2[7] : group_index==2 ? y_n2[11] : y_n2[15])),
      .i_n(engine_i[3]),
      .y_n(engine_y[3]),
      .valid_out(engine_done[3]));
  end
  endgenerate

  always_ff @(posedge clk_in)begin
    if(rst_in)begin
      group_index<=0;engine_launch<=0;engine_busy<=0;filters_valid_out<=0;
      for(integer k=0;k<N_FILTERS;k=k+1)begin i_n[k]<=0;y_n[k]<=0;end
    end else begin
      engine_launch<=0;filters_valid_out<=0;
      if(filters_valid_in&&!engine_busy)begin
        group_index<=0;engine_launch<=1;engine_busy<=1;
      end else if(engine_busy&&(&engine_done))begin
        if(group_index==0)begin i_n[0]<=engine_i[0];y_n[0]<=engine_y[0];end
        if(group_index==0)begin i_n[1]<=engine_i[1];y_n[1]<=engine_y[1];end
        if(group_index==0)begin i_n[2]<=engine_i[2];y_n[2]<=engine_y[2];end
        if(group_index==0)begin i_n[3]<=engine_i[3];y_n[3]<=engine_y[3];end
        if(group_index==1)begin i_n[4]<=engine_i[0];y_n[4]<=engine_y[0];end
        if(group_index==1)begin i_n[5]<=engine_i[1];y_n[5]<=engine_y[1];end
        if(group_index==1)begin i_n[6]<=engine_i[2];y_n[6]<=engine_y[2];end
        if(group_index==1)begin i_n[7]<=engine_i[3];y_n[7]<=engine_y[3];end
        if(group_index==2)begin i_n[8]<=engine_i[0];y_n[8]<=engine_y[0];end
        if(group_index==2)begin i_n[9]<=engine_i[1];y_n[9]<=engine_y[1];end
        if(group_index==2)begin i_n[10]<=engine_i[2];y_n[10]<=engine_y[2];end
        if(group_index==2)begin i_n[11]<=engine_i[3];y_n[11]<=engine_y[3];end
        if(group_index==3)begin i_n[12]<=engine_i[0];y_n[12]<=engine_y[0];end
        if(group_index==3)begin i_n[13]<=engine_i[1];y_n[13]<=engine_y[1];end
        if(group_index==3)begin i_n[14]<=engine_i[2];y_n[14]<=engine_y[2];end
        if(group_index==3)begin i_n[15]<=engine_i[3];y_n[15]<=engine_y[3];end
        if(group_index==GROUPS-1)begin
          filters_valid_out<={N_FILTERS{1'b1}};engine_busy<=0;
        end else begin group_index<=group_index+1;engine_launch<=1;end
      end
    end
  end


  always_ff @(posedge clk_in) begin
    if (rst_in) begin
      state <= WAITING;
      valid_out <= 0;
      filters_valid_in <= 0;
      for (int j=0;j<N_FILTERS;j++) begin
        x_n[j]<=0; x_n1[j]<=0; x_n2[j]<=0;
        i_n1[j]<=0; i_n2[j]<=0; y_n1[j]<=0; y_n2[j]<=0;
        for(int k=0;k<10;k++) coeffs[(j)*10+(k)]<=0;
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
              for (int j = 0; j < 10; j++) coeffs[(i)*10+(j)] <= COEFFS[i*10+j];
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
              for (int j = 0; j < 10; j++) coeffs[(i)*10+(j)] <= COEFFS[N_FILTERS*10+j];
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
              for (int j = 0; j < 10; j++) coeffs[(i)*10+(j)] <= COEFFS[i*10+j];
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
