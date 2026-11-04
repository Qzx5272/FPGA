// Dynamic parameter speech: 64 additive partials, internally timed phoneme score.
// ROM contains spectral weights / pitch / noise gain, never recorded PCM.
module hello_engine(input clk,rst,sample_tick,panic,enable,gate,slow,
    input [6:0] volume,velocity,
    output reg signed [15:0] sample,output reg active);
    reg [15:0] hello_weights[0:8191];
    reg [31:0] pitch_rom[0:127];
    reg [7:0] noise_rom[0:127];
    initial begin
        `include "hello_rom.vh"
    end
    `include "sine_function.vh"
    reg prev_gate;
    reg [6:0] frame;
    reg [9:0] elapsed;
    reg [5:0] harmonic;
    reg [3:0] stage;
    reg [31:0] phase,partial_phase,inc,target_inc,lfsr;
    reg [15:0] smooth[0:63],target_weight;
    reg [12:0] addr;
    reg [7:0] noise_target,noise_gain;
    reg [6:0] volume_smooth;
    reg signed [31:0] product,raw;
    reg signed [35:0] accumulator;
    reg signed [48:0] scaled;
    reg signed [23:0] noise_fast,noise_slow;
    reg signed [32:0] breath;
    integer k;
    always @(posedge clk) begin
        if(rst||panic||!enable||!gate)begin
            active<=0;sample<=0;prev_gate<=0;frame<=0;elapsed<=0;
            harmonic<=0;stage<=15;phase<=0;partial_phase<=0;
            inc<=12079596;target_inc<=12079596;lfsr<=32'h13579bdf;
            target_weight<=0;addr<=0;noise_target<=0;noise_gain<=0;
            volume_smooth<=0;product<=0;raw<=0;accumulator<=0;scaled<=0;
            noise_fast<=0;noise_slow<=0;breath<=0;
            for(k=0;k<64;k=k+1)smooth[k]<=0;
        end else if(sample_tick)begin
            prev_gate<=gate;
            if(!prev_gate)begin active<=1;frame<=0;elapsed<=0;end
            else if(active)begin
                if(elapsed==(slow?719:479))begin
                    elapsed<=0;
                    if(frame==127)begin active<=0;sample<=0;end
                    else frame<=frame+1;
                end else elapsed<=elapsed+1;
            end
            if(active)begin
                stage<=0;harmonic<=0;accumulator<=0;
                addr<={frame,6'b0};target_inc<=pitch_rom[frame];noise_target<=noise_rom[frame];
                if(inc<target_inc)inc<=inc+((target_inc-inc+127)>>7);
                else if(inc>target_inc)inc<=inc-((inc-target_inc+127)>>7);
                phase<=phase+inc;partial_phase<=phase+inc;
                if(noise_gain<noise_target)noise_gain<=noise_gain+1;
                else if(noise_gain>noise_target)noise_gain<=noise_gain-1;
                if(volume_smooth<volume)volume_smooth<=volume_smooth+1;
                else if(volume_smooth>volume)volume_smooth<=volume_smooth-1;
                lfsr<={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
                // Broad aspiration band: roughly 200-2000 Hz, not a stored /h/.
                noise_fast<=noise_fast+(($signed(lfsr[31:16])-$signed(noise_fast))>>>2);
                noise_slow<=noise_slow+(($signed(lfsr[31:16])-$signed(noise_slow))>>>5);
                breath<=($signed(noise_fast)-$signed(noise_slow))*$signed({1'b0,noise_gain});
            end
        end else case(stage)
            0:begin target_weight<=hello_weights[addr+harmonic];stage<=1;end
            1:begin
                if(smooth[harmonic]<target_weight)smooth[harmonic]<=smooth[harmonic]+((target_weight-smooth[harmonic]+63)>>6);
                else if(smooth[harmonic]>target_weight)smooth[harmonic]<=smooth[harmonic]-((smooth[harmonic]-target_weight+63)>>6);
                stage<=2;
            end
            2:begin product<=$signed(sine(partial_phase[31:24]))*$signed({1'b0,smooth[harmonic]});stage<=3;end
            3:begin
                accumulator<=accumulator+product;partial_phase<=partial_phase+phase;
                if(harmonic==63)stage<=4;else begin harmonic<=harmonic+1;stage<=0;end
            end
            4:begin raw<=($signed(accumulator)>>>13)+($signed(breath)>>>10);stage<=5;end
            5:begin scaled<=$signed(raw)*$signed({1'b0,velocity});stage<=6;end
            6:begin scaled<=($signed(scaled)>>>7)*$signed({1'b0,volume_smooth});stage<=7;end
            7:begin
                if(!active)sample<=0;
                else if(($signed(scaled)>>>7)>32767)sample<=32767;
                else if(($signed(scaled)>>>7)<-32768)sample<=-32768;
                else sample<=$signed(scaled)>>>7;
                stage<=15;
            end
        endcase
    end
endmodule
