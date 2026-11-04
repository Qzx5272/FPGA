// Real-time 32-partial additive voice prototype. No recorded samples.
// Profile ROM derives from GPL-3.0-or-later eSpeak data; see voice/README.md.
module voice_engine(input clk,rst,sample_tick,panic,enable,
    input [7:0] keys, input [2:0] octave,unit,
    input [6:0] volume,velocity, input [15:0] attack_step,release_step,
    output reg signed [15:0] sample, output wire active);
    reg [15:0] weights[0:16383];
    initial begin
        `include "voice_rom.vh"
    end
    `include "sine_function.vh"
    reg [31:0] phase,partial_phase;
    reg [15:0] envelope;
    reg [15:0] smooth[0:31];
    reg [4:0] harmonic;
    reg [3:0] stage;
    reg [13:0] address;
    reg [15:0] target_weight;
    reg signed [31:0] product;
    reg signed [35:0] accumulator;
    reg signed [31:0] raw;
    reg signed [48:0] scaled;
    reg [31:0] noise;
    reg signed [17:0] filtered_noise;
    reg [6:0] vol_smooth;
    integer k,note;
    reg found;
    reg [31:0] base,inc;
    always @* begin
        note=0;found=0;
        for(integer j=0;j<8;j=j+1) if(keys[j]&&!found) begin note=j;found=1;end
        case(note)
        0:base=23409859;1:base=26276679;2:base=29494575;3:base=31248413;
        4:base=35075158;5:base=39370534;6:base=44191930;default:base=46819719;
        endcase
        inc=octave>=4 ? base<<(octave-4) : base>>(4-octave);
    end
    assign active=envelope!=0;
    always @(posedge clk) begin
        if(rst||panic||!enable) begin
            sample<=0;phase<=0;partial_phase<=0;envelope<=0;stage<=15;
            harmonic<=0;address<=0;target_weight<=0;product<=0;accumulator<=0;
            raw<=0;scaled<=0;noise<=32'h13579bdf;filtered_noise<=0;vol_smooth<=0;
            for(k=0;k<32;k=k+1)smooth[k]<=0;
        end else if(sample_tick) begin
            if(keys!=0) begin
                if({1'b0,envelope}+{1'b0,attack_step}>=65535)envelope<=65535;
                else envelope<=envelope+attack_step;
            end else if(envelope<=release_step)envelope<=0;
            else envelope<=envelope-release_step;
            if(vol_smooth<volume)vol_smooth<=vol_smooth+1;
            else if(vol_smooth>volume)vol_smooth<=vol_smooth-1;
            phase<=phase+inc;partial_phase<=phase+inc;
            harmonic<=0;accumulator<=0;stage<=0;
            address<=(unit==7?0:unit)*2048+((octave-2)*8+note)*32;
            noise<={noise[30:0],noise[31]^noise[21]^noise[1]^noise[0]};
            filtered_noise<=filtered_noise+(($signed(noise[31:16])-$signed(filtered_noise))>>>2);
        end else case(stage)
            0:begin target_weight<=weights[address+harmonic];stage<=1;end
            1:begin
                if(smooth[harmonic]<target_weight)
                    smooth[harmonic]<=smooth[harmonic]+((target_weight-smooth[harmonic]+31)>>5);
                else if(smooth[harmonic]>target_weight)
                    smooth[harmonic]<=smooth[harmonic]-((smooth[harmonic]-target_weight+31)>>5);
                stage<=2;
            end
            2:begin product<=$signed(sine(partial_phase[31:24]))*$signed({1'b0,smooth[harmonic]});stage<=3;end
            3:begin
                accumulator<=accumulator+product;partial_phase<=partial_phase+phase;
                if(harmonic==31)stage<=4;else begin harmonic<=harmonic+1;stage<=0;end
            end
            4:begin raw<=unit==7?($signed(filtered_noise)>>>2):($signed(accumulator)>>>14);stage<=5;end
            5:begin scaled<=$signed(raw)*$signed({1'b0,envelope});stage<=6;end
            6:begin scaled<=($signed(scaled)>>>16)*$signed({1'b0,velocity});stage<=7;end
            7:begin scaled<=($signed(scaled)>>>7)*$signed({1'b0,vol_smooth});stage<=8;end
            8:begin
                if(($signed(scaled)>>>7)>32767)sample<=32767;
                else if(($signed(scaled)>>>7)<-32768)sample<=-32768;
                else sample<=$signed(scaled)>>>7;
                stage<=15;
            end
        endcase
    end
endmodule
