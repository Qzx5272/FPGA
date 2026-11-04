// 50 MHz, 115200 8N1; receiver validates start and stop bits.
module uart_rx #(parameter DIV=434)(input clk, input rst, input rx,
    output reg [7:0] data, output reg valid);
    reg [1:0] sync;
    reg [2:0] state, bitno;
    reg [15:0] count;
    reg [7:0] shift;
    always @(posedge clk) begin
        if(rst) begin sync<=3; state<=0; count<=0; valid<=0; data<=0; shift<=0; bitno<=0; end
        else begin
            sync <= {sync[0],rx}; valid<=0;
            case(state)
            0: if(!sync[1]) begin count<=DIV/2-1; state<=1; end
            1: if(count!=0) count<=count-1; else if(!sync[1]) begin count<=DIV-1; bitno<=0; state<=2; end else state<=0;
            2: if(count!=0) count<=count-1; else begin
                shift[bitno]<=sync[1]; count<=DIV-1;
                if(bitno==7) state<=3; else bitno<=bitno+1;
            end
            3: if(count!=0) count<=count-1; else begin
                if(sync[1]) begin data<=shift; valid<=1; end
                state<=0;
            end
            default: state<=0;
            endcase
        end
    end
endmodule

module uart_tx #(parameter DIV=434)(input clk, input rst, input [7:0] data,
    input start, output reg tx, output reg busy);
    reg [9:0] shift;
    reg [3:0] bitno;
    reg [15:0] count;
    always @(posedge clk) begin
        if(rst) begin tx<=1; busy<=0; shift<=10'h3ff; bitno<=0; count<=0; end
        else if(!busy) begin
            tx<=1;
            if(start) begin shift<={1'b1,data,1'b0}; tx<=0; busy<=1; count<=DIV-1; bitno<=0; end
        end else if(count!=0) count<=count-1;
        else if(bitno==9) begin busy<=0; tx<=1; end
        else begin shift<={1'b1,shift[9:1]}; tx<=shift[1]; bitno<=bitno+1; count<=DIV-1; end
    end
endmodule
