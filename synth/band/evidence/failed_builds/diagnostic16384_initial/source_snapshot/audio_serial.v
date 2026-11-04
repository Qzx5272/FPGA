// Fractional clock enable: average Fs=48 kHz from 50 MHz. Edge jitter <=20 ns.
// All logic stays in the 50 MHz domain; BCK is only an output, not an internal clock.
// MODE_I2S=0: PT8211, 16-bit right justified, WS low=right.
// MODE_I2S=1: standard I2S, 16-bit slots, WS changes one bit before MSB, low=left.
module audio_serial #(parameter MODE_I2S=0)(
    input clk, input rst, input signed [15:0] left, right,
    output reg bck, ws, din, output reg sample_tick);
    reg [25:0] accum;
    reg [4:0] bitpos;
    reg [15:0] hold_left, hold_right;
    wire [26:0] next_accum = {1'b0,accum} + 27'd3072000;
    always @(posedge clk) begin
        if(rst) begin
            accum<=0; bck<=1; ws<=MODE_I2S?1:0; din<=0;
            bitpos<=0; hold_left<=0; hold_right<=0; sample_tick<=0;
        end else begin
            sample_tick<=0;
            if(next_accum>=50000000) begin
                accum<=next_accum-50000000; bck<=~bck;
                if(bck) begin // falling edge: data changes, DAC samples rising edge
                    if(bitpos==0) begin
                        hold_left<=left; hold_right<=right; sample_tick<=1;
                    end
                    if(MODE_I2S) begin
                        // slots begin at their MSB; WS leads them by one bit.
                        ws <= (bitpos>=15 && bitpos<31);
                        if(bitpos<16) din <= bitpos==0 ? left[15] : hold_left[15-bitpos];
                        else din <= hold_right[31-bitpos];
                    end else begin
                        ws <= bitpos[4];
                        if(bitpos<16) din <= bitpos==0 ? right[15] : hold_right[15-bitpos];
                        else din <= hold_left[31-bitpos];
                    end
                    bitpos<=bitpos+1'b1;
                end
            end else accum<=next_accum[25:0];
        end
    end
endmodule
