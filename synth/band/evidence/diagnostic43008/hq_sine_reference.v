// Symmetry-compressed candidate: one 1024x34 paired-endpoint ROM read.
// Same four registered stages and interface as hq_sine.
module hq_sine_reference #(
    parameter ROM_FILE="sine_quarter.bin"
)(input wire clk,input wire rst,input wire valid_in,input wire [31:0] phase,
  output reg valid_out,output reg signed [17:0] sample);
    reg [33:0] lut[0:1023];initial begin
        `include "sine_quarter_reference.vh"
    end
    wire [9:0] address=phase[30] ? ~phase[29:20] : phase[29:20];
    reg [33:0] pair0;reg mirror0,negative0,negative1,negative2;
    reg [19:0] frac0,frac1;reg signed [17:0] a1,a2;
    reg signed [9:0] delta1;reg signed [30:0] product2;
    reg v0,v1,v2;
    wire signed [17:0] lo={1'b0,pair0[16:0]};
    wire signed [17:0] hi={1'b0,pair0[33:17]};
    wire signed [17:0] a0=mirror0 ? hi:lo;
    wire signed [17:0] b0=mirror0 ? lo:hi;
    wire signed [18:0] delta={b0[17],b0}-{a0[17],a0};
    wire signed [31:0] rounded={product2[30],product2}+32'sd524288;
    wire signed [31:0] correction=rounded >>> 20;
    wire signed [31:0] extended={{14{a2[17]}},a2};
    wire signed [31:0] interpolated=extended+correction;
    always @(posedge clk) begin
        pair0<=lut[address];mirror0<=phase[30];negative0<=phase[31];frac0<=phase[19:0];
        a1<=a0;delta1<=delta[9:0];frac1<=frac0;negative1<=negative0;
        a2<=a1;product2<=delta1*$signed({1'b0,frac1});negative2<=negative1;
        sample<=negative2 ? -interpolated[17:0]:interpolated[17:0];
        if(rst)begin v0<=0;v1<=0;v2<=0;valid_out<=0;sample<=0;end
        else begin v0<=valid_in;v1<=v0;v2<=v1;valid_out<=v2;end
    end
endmodule
