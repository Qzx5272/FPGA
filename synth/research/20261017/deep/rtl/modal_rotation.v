// Research arithmetic kernel: S(36,32) state, S(24,21) coefficients.
// Four products use the OLD x,y state. Caller schedules distinct state slots.
// Input accepted at edge n; output at edge n+2. Explicit saturation telemetry.
module modal_rotation(input wire clk,input wire rst,input wire valid_in,
    input wire signed [35:0] x,y,drive,
    input wire signed [23:0] a,b,
    output reg valid_out,output reg signed [35:0] next_x,next_y,
    output reg saturated);
    reg signed [59:0] ax,by,bx,ay;
    reg signed [35:0] drive0;
    reg signed [63:0] sumx,sumy;
    reg v0,v1;
    wire signed [63:0] axe={{4{ax[59]}},ax},bye={{4{by[59]}},by};
    wire signed [63:0] bxe={{4{bx[59]}},bx},aye={{4{ay[59]}},ay};
    wire signed [63:0] de={{28{drive0[35]}},drive0};
    function signed [63:0] round21;
        input signed [63:0] z;
        begin
            if(z>=0)round21=(z+64'sd1048576)>>>21;
            else round21=-(((-z)+64'sd1048576)>>>21);
        end
    endfunction
    wire signed [63:0] rx=round21(sumx),ry=round21(sumy);
    wire sx=rx>64'sd34359738367 || rx< -64'sd34359738368;
    wire sy=ry>64'sd34359738367 || ry< -64'sd34359738368;
    always @(posedge clk)begin
        ax<=a*x;by<=b*y;bx<=b*x;ay<=a*y;drive0<=drive;
        sumx<=axe-bye+(de<<<21);sumy<=bxe+aye;
        next_x<=sx ? (rx[63] ? -36'sd34359738368:36'sd34359738367):rx[35:0];
        next_y<=sy ? (ry[63] ? -36'sd34359738368:36'sd34359738367):ry[35:0];
        saturated<=sx|sy;
        if(rst)begin v0<=0;v1<=0;valid_out<=0;saturated<=0;next_x<=0;next_y<=0;end
        else begin v0<=valid_in;v1<=v0;valid_out<=v1;end
    end
endmodule
