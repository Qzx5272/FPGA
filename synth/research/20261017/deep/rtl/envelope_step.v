// Research kernel, not integrated. rate is nonnegative, Q24, <= 2^24.
// Remainder carries rounding error; caller resets it at segment transitions.
// Input edge n -> output edge n+3, II=1 across distinct state addresses.
module envelope_step(input wire clk,rst,valid_in,
    input wire [23:0] env,target,
    input wire [26:0] rate,
    input wire signed [24:0] remainder,
    output reg valid_out,
    output reg [23:0] next_env,
    output reg signed [24:0] next_remainder);
    wire signed [24:0] diff=$signed({1'b0,target})-$signed({1'b0,env});
    wire signed [26:0] sr=$signed(rate);
    reg signed [51:0] product;
    reg signed [24:0] rem0;
    reg [23:0] e0,e1,e2;
    reg signed [52:0] z1,z2,delta2;
    reg v0,v1,v2;
    function signed [52:0] round24;
        input signed [52:0] z;
        begin
            if(z>=0)round24=(z+53'sd8388608)>>>24;
            else round24=-(((-z)+53'sd8388608)>>>24);
        end
    endfunction
    wire signed [52:0] new_value=$signed({29'd0,e2})+delta2;
    wire signed [52:0] remainder_full=z2-(delta2<<<24);
    always @(posedge clk)begin
        product<=diff*sr;rem0<=remainder;e0<=env;
        z1<=$signed({product[51],product})+$signed({{28{rem0[24]}},rem0});e1<=e0;
        delta2<=round24(z1);z2<=z1;e2<=e1;
        // Valid inputs remain in [0,2^24-1]; clamps also bound corrupt commands.
        if(new_value<0)begin next_env<=0;next_remainder<=0;end
        else if(new_value>53'sd16777215)begin next_env<=24'hffffff;next_remainder<=0;end
        else begin next_env<=new_value[23:0];next_remainder<=remainder_full[24:0];end
        if(rst)begin v0<=0;v1<=0;v2<=0;valid_out<=0;next_env<=0;next_remainder<=0;end
        else begin v0<=valid_in;v1<=v0;v2<=v1;valid_out<=v2;end
    end
endmodule
