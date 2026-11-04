`timescale 1ns / 1ps
`default_nettype none

module double_biquad #(parameter SHIFT = 20, parameter COEFF_WIDTH = 32)
(
  // [a1_0, a2_0, b0_0, b1_0, b2_0, a1_1, a2_1, b0_1, b1_1, b2_1]
  //input wire signed [31:0] coeffs [9:0],
  input wire clk_in,
  input wire rst_in,
  input wire valid_in,
  input wire signed [31:0] b0_0,
  input wire signed [31:0] b1_0,
  input wire signed [31:0] b2_0,
  input wire signed [31:0] a1_0,
  input wire signed [31:0] a2_0,

  input wire signed [31:0] b0_1,
  input wire signed [31:0] b1_1,
  input wire signed [31:0] b2_1,
  input wire signed [31:0] a1_1,
  input wire signed [31:0] a2_1,

  input wire signed [31:0] x_n,
  input wire signed [31:0] x_n1,
  input wire signed [31:0] x_n2,
  input wire signed [31:0] i_n1,
  input wire signed [31:0] i_n2,
  input wire signed [31:0] y_n1,
  input wire signed [31:0] y_n2,
  output logic signed [31:0] i_n,
  output logic signed [31:0] y_n,
  output logic valid_out
);

  typedef enum {
    WAITING,
    A0, A1, B0, B1, C0, C1, D0, D1, E0, E1,
    S1, S2, S3, S4,

    F0, F1, G0, G1, H0, H1, I0, I1, J0, J1,
    T1, T2, T3, T4
    , AM, BM, CM, DM, EM, FM, GM, HM, IM, JM
  } state_t;
  state_t state;

  // Direct Form I
  // i[n] = b0_0*x[n] + b1_0*x[n-1] + b2_0*x[n-2] - a1_0*i[n-1] - a2_0*i[n-2]
  // y[n] = b0_1*i[n] + b1_1*i[n-1] + b2_1*i[n-2] - a1_1*y[n-1] - a2_0*y[n-2]
  logic signed [63:0] temp;
  // One explicitly shared multiplier, selected by the sequential state.
  logic signed [31:0] mul_a, mul_b;
  // Register selected operands before the shared32x32 multiplier.
  logic signed [COEFF_WIDTH-1:0] operand_a;
  logic signed [31:0] operand_b;
  wire signed [63:0] mul_result = operand_a * operand_b;
  always_comb begin
    mul_a=0;mul_b=0;
    case(state)
      A0: begin mul_a=b0_0;mul_b=x_n;end
      B0: begin mul_a=a1_0;mul_b=i_n1;end
      C0: begin mul_a=b1_0;mul_b=x_n1;end
      D0: begin mul_a=a2_0;mul_b=i_n2;end
      E0: begin mul_a=b2_0;mul_b=x_n2;end
      F0: begin mul_a=b0_1;mul_b=i_n;end
      G0: begin mul_a=a1_1;mul_b=y_n1;end
      H0: begin mul_a=b1_1;mul_b=i_n1;end
      I0: begin mul_a=a2_1;mul_b=y_n2;end
      J0: begin mul_a=b2_1;mul_b=i_n2;end
      default: begin mul_a=0;mul_b=0;end
    endcase
  end


  always_ff @(posedge clk_in) begin
    if (rst_in) begin
      y_n <= 0;
      i_n <= 0;
      temp <= 0;operand_a<=0;operand_b<=0;
      valid_out <= 0;
      state <= WAITING;
    end else begin
      case (state)
        WAITING: begin
          valid_out <= 0;
          if (valid_in) begin
            state <= A0;
          end
        end

        // Interleave additions and subtractions to minimize bit growth
        // First biquad
        A0: begin operand_a<=mul_a;operand_b<=mul_b;state<=AM;end
        AM: begin temp<=mul_result;state<=A1;end
        A1: begin i_n <= temp >>> SHIFT;  state <= B0; end

        B0: begin operand_a<=mul_a;operand_b<=mul_b;state<=BM;end
        BM: begin temp<=mul_result;state<=B1;end
        B1: begin temp <= temp >>> SHIFT; state <= S1; end

        S1: begin i_n <= i_n - temp;      state <= C0; end

        C0: begin operand_a<=mul_a;operand_b<=mul_b;state<=CM;end
        CM: begin temp<=mul_result;state<=C1;end
        C1: begin temp <= temp >>> SHIFT; state <= S2; end
  
        S2: begin i_n <= i_n + temp;      state <= D0; end

        D0: begin operand_a<=mul_a;operand_b<=mul_b;state<=DM;end
        DM: begin temp<=mul_result;state<=D1;end
        D1: begin temp <= temp >>> SHIFT; state <= S3; end

        S3: begin i_n <= i_n - temp;      state <= E0; end

        E0: begin operand_a<=mul_a;operand_b<=mul_b;state<=EM;end
        EM: begin temp<=mul_result;state<=E1;end
        E1: begin temp <= temp >>> SHIFT; state <= S4; end
        
        S4: begin i_n <= i_n + temp;      state <= F0; end

        // Second biquad
        F0: begin operand_a<=mul_a;operand_b<=mul_b;state<=FM;end
        FM: begin temp<=mul_result;state<=F1;end
        F1: begin y_n <= temp >>> SHIFT;  state <= G0; end

        G0: begin operand_a<=mul_a;operand_b<=mul_b;state<=GM;end
        GM: begin temp<=mul_result;state<=G1;end
        G1: begin temp <= temp >>> SHIFT; state <= T1; end

        T1: begin y_n <= y_n - temp;      state <= H0; end

        H0: begin operand_a<=mul_a;operand_b<=mul_b;state<=HM;end
        HM: begin temp<=mul_result;state<=H1;end
        H1: begin temp <= temp >>> SHIFT; state <= T2; end
  
        T2: begin y_n <= y_n + temp;      state <= I0; end

        I0: begin operand_a<=mul_a;operand_b<=mul_b;state<=IM;end
        IM: begin temp<=mul_result;state<=I1;end
        I1: begin temp <= temp >>> SHIFT; state <= T3; end

        T3: begin y_n <= y_n - temp;      state <= J0; end

        J0: begin operand_a<=mul_a;operand_b<=mul_b;state<=JM;end
        JM: begin temp<=mul_result;state<=J1;end
        J1: begin temp <= temp >>> SHIFT; state <= T4; end
        
        T4: begin
          y_n <= y_n + temp;
          state <= WAITING;
          valid_out <= 1;
        end
      endcase
    end
  end

endmodule

`default_nettype wire
