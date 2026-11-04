// 16 eighth-note events. Timing and note generation execute entirely in FPGA.
// A sample-domain accumulator avoids a variable divider and preserves tempo.
module auto_accompaniment(input clk,rst,tick,panic,enabled,
    input [5:0] tempo_code, output reg [7:0] keys,
    output reg [3:0] position);
    reg [20:0] beat;
    wire [7:0] bpm=8'd40+{tempo_code,1'b0};
    reg [7:0] chord,melody;
    always @* begin
        case(position[3:2])
            0:chord=8'h15; // C E G
            1:chord=8'ha8; // F A C
            2:chord=8'h52; // G B D
            default:chord=8'h15;
        endcase
        case(position)
            0,8:melody=8'h01;
            1,9:melody=8'h04;
            2,6,10:melody=8'h10;
            3,7:melody=8'h80;
            4,12:melody=8'h08;
            5,13:melody=8'h20;
            11:melody=8'h40;
            14:melody=8'h02;
            default:melody=8'h01;
        endcase
    end
    always @(posedge clk) begin
        if(rst || panic || !enabled) begin beat<=0;position<=0;keys<=0;end
        else if(tick) begin
            if(beat+bpm>=21'd1440000) begin beat<=beat+bpm-21'd1440000;position<=position+1;end
            else beat<=beat+bpm;
            // Short release gap retriggers the next step, even on repeated notes.
            keys<=beat<21'd1224000 ? (melody | (position[0]?8'd0:chord)) : 8'd0;
        end
    end
endmodule
