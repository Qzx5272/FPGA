// Research candidate only; not connected to the production audio top.
// 4096 x signed 18-bit analytic sine table, adjacent-point interpolation.
// Two synchronous reads per input; one 21 x 10 signed multiply per cycle.
// Input at edge n produces valid output at edge n+3 (four registered stages).
module hq_sine #(
    parameter ROM_FILE = "sine4096.hex"
)(
    input wire clk, input wire rst,
    input wire valid_in, input wire [31:0] phase,
    output reg valid_out, output reg signed [17:0] sample
);
    reg signed [17:0] lut [0:4095];
    initial $readmemh(ROM_FILE,lut);
    reg signed [17:0] a0,b0,a1,a2;
    reg [19:0] frac0,frac1;
    reg signed [9:0] delta1;
    reg signed [30:0] product2;
    reg v0,v1,v2;
    wire signed [18:0] difference = {b0[17],b0}-{a0[17],a0};
    wire signed [31:0] rounded = {product2[30],product2}+32'sd524288;
    wire signed [31:0] correction = rounded >>> 20;
    wire signed [31:0] base_extended = {{14{a2[17]}},a2};
    wire signed [31:0] interpolated = base_extended+correction;
    wire [11:0] next_index = phase[31:20]+12'd1;
    always @(posedge clk) begin
        a0 <= lut[phase[31:20]];
        b0 <= lut[next_index];
        frac0 <= phase[19:0];
        a1 <= a0;
        // Generated ROM is checked separately: abs(adjacent difference)<=202.
        delta1 <= difference[9:0];
        frac1 <= frac0;
        a2 <= a1;
        product2 <= delta1 * $signed({1'b0,frac1});
        sample <= interpolated[17:0];
        if(rst) begin
            v0<=0;v1<=0;v2<=0;valid_out<=0;sample<=0;
        end else begin
            v0<=valid_in;v1<=v0;v2<=v1;valid_out<=v2;
        end
    end
endmodule
