module control #(parameter WATCHDOG=25000000)(
    input clk, input rst, input [7:0] rx_data, input rx_valid,
    output reg [7:0] keys, sequence, brightness,
    output reg [2:0] octave, output reg [1:0] tone,
    output reg [6:0] volume, velocity,
    output reg [15:0] attack_step, release_step,
    output reg panic, packet_valid, online,
    output reg auto_play, output reg [5:0] tempo_code);
    reg [7:0] bufdata [0:12];
    reg [4:0] pos;
    reg [7:0] checksum;
    reg [25:0] watchdog;
    reg [19:0] byte_timeout;
    always @(posedge clk) begin
        if(rst) begin
            keys<=0; sequence<=0; brightness<=80; octave<=4; tone<=0;
            volume<=32; velocity<=100; attack_step<=91; release_step<=4;
            panic<=1; packet_valid<=0; online<=0; pos<=0; checksum<=0;
            watchdog<=0; byte_timeout<=0; auto_play<=0; tempo_code<=28;
        end else begin
            panic<=0; packet_valid<=0;
            if(watchdog < WATCHDOG) watchdog<=watchdog+1;
            else begin keys<=0; online<=0; panic<=1; auto_play<=0; end
            if(pos!=0) begin
                if(byte_timeout==500000) begin pos<=0; byte_timeout<=0; end
                else byte_timeout<=byte_timeout+1;
            end
            if(rx_valid) begin
                byte_timeout<=0;
                case(pos)
                0: if(rx_data==8'ha5) pos<=1;
                1: if(rx_data==8'h5a) begin pos<=2; checksum<=0; end else if(rx_data!=8'ha5) pos<=0;
                14: begin
                    pos<=0;
                    if(rx_data==checksum && bufdata[2]>=2 && bufdata[2]<=6 && bufdata[3]<=3 &&
                       !bufdata[5][7] && !bufdata[6][7] && {bufdata[8],bufdata[7]}!=0 &&
                       {bufdata[10],bufdata[9]}!=0) begin
                        sequence<=bufdata[0]; keys<=bufdata[11][0]?0:bufdata[1]; octave<=bufdata[2][2:0];
                        tone<=bufdata[3][1:0]; brightness<=bufdata[4]; volume<=bufdata[5][6:0]; velocity<=bufdata[6][6:0];
                        attack_step<={bufdata[8],bufdata[7]}; release_step<={bufdata[10],bufdata[9]};
                        auto_play<=bufdata[11][1] && !bufdata[11][0]; tempo_code<=bufdata[11][7:2];
                        panic<=bufdata[11][0]; packet_valid<=1; online<=1; watchdog<=0;
                    end
                end
                default: begin bufdata[pos-2]<=rx_data; checksum<=checksum ^ rx_data; pos<=pos+1; end
                endcase
            end
        end
    end
endmodule
