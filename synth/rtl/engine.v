// Eight independent DDS voices, three additive partials each. No recorded PCM.
// Shared interpolated 4096-point sine pipeline; finishes within 40 clocks.
module engine(input clk, rst, sample_tick, panic,
    input [7:0] keys, brightness, input [2:0] octave, input [1:0] tone,
    input [6:0] volume, velocity, input [15:0] attack_step, release_step,
    output reg signed [15:0] sample, output reg [3:0] voices);
    reg [31:0] phase[0:7];
    reg [15:0] env[0:7];
    reg [2:0] state[0:7]; // idle,attack,decay,sustain,release
    reg [6:0] vel[0:7];
    reg [7:0] prev_keys;
    reg [5:0] stage;
    reg [4:0] received;
    reg [31:0] lookup_phase;
    wire lookup_valid;
    wire signed [17:0] lookup_sample;
    always @* begin
        lookup_phase=0;
        if(stage<24) case(stage%3)
            0:lookup_phase=phase[stage/3];
            1:lookup_phase=phase[stage/3]<<1;
            2:lookup_phase=phase[stage/3]+(phase[stage/3]<<1);
        endcase
    end
    hq_sine_quarter oscillator(clk,rst||panic,stage<24,lookup_phase,lookup_valid,lookup_sample);
    reg [7:0] bright_smooth;
    reg [6:0] volume_smooth;
    reg signed [15:0] s1[0:7],s2[0:7],s3[0:7];
    reg signed [24:0] harmonics[0:7];
    reg signed [17:0] waveval[0:7];
    reg signed [34:0] enveloped[0:7];
    reg signed [26:0] with_velocity[0:7];
    reg signed [20:0] pair[0:3];
    reg signed [22:0] total;
    reg signed [30:0] gained;
    integer i,k;
    `include "sine_function.vh"
    function [31:0] increment;
        input integer key;
        input [2:0] oct;
        reg [31:0] base;
        begin
            case(key)
            0:base=23409859; 1:base=26276679; 2:base=29494575; 3:base=31248413;
            4:base=35075158; 5:base=39370534; 6:base=44191930; default:base=46819719;
            endcase
            increment=(oct>=4)?(base<<(oct-4)):(base>>(4-oct));
        end
    endfunction
    wire [15:0] sustain = tone==2 ? 16'd0 : (tone==1 ? 16'd40000 : 16'd49152);
    wire [15:0] decay_step = tone==2 ? 16'd6 : 16'd4;
    reg [3:0] active_count;
    always @* begin
        active_count=0;
        for(k=0;k<8;k=k+1) if(env[k]!=0) active_count=active_count+1;
    end
    always @(posedge clk) begin
        if(rst || panic) begin
            sample<=0; voices<=0; prev_keys<=0; stage<=63; received<=0; bright_smooth<=80; volume_smooth<=0;
            total<=0; gained<=0;
            for(i=0;i<8;i=i+1) begin
                phase[i]<=0; env[i]<=0; state[i]<=0; vel[i]<=0;
                s1[i]<=0; s2[i]<=0; s3[i]<=0; harmonics[i]<=0;
                waveval[i]<=0; enveloped[i]<=0; with_velocity[i]<=0;
            end
            for(i=0;i<4;i=i+1) pair[i]<=0;
        end else if(sample_tick) begin
            stage<=0; received<=0; prev_keys<=keys; voices<=active_count;
            if(bright_smooth<brightness) bright_smooth<=bright_smooth+1;
            else if(bright_smooth>brightness) bright_smooth<=bright_smooth-1;
            if(volume_smooth<volume) volume_smooth<=volume_smooth+1;
            else if(volume_smooth>volume) volume_smooth<=volume_smooth-1;
            for(i=0;i<8;i=i+1) begin
                phase[i]<=phase[i]+increment(i,octave);
                if(keys[i] && !prev_keys[i]) begin state[i]<=1; vel[i]<=velocity; end
                else if(!keys[i] && prev_keys[i]) state[i]<=4;
                else case(state[i])
                1: if({1'b0,env[i]}+{1'b0,attack_step}>=17'd65535) begin env[i]<=65535; state[i]<=2; end
                   else env[i]<=env[i]+attack_step;
                2: if(env[i]<=sustain+decay_step) begin env[i]<=sustain; state[i]<=3; end
                   else env[i]<=env[i]-decay_step;
                3: env[i]<=sustain;
                4: if(env[i]<=release_step) begin env[i]<=0; state[i]<=0; end
                   else env[i]<=env[i]-release_step;
                default: env[i]<=0;
                endcase
            end
        end else begin
            if(stage<40) stage<=stage+1;
            if(lookup_valid && received<24) begin
                case(received%3)
                    0:s1[received/3]<=lookup_sample>>>2;
                    1:s2[received/3]<=lookup_sample>>>2;
                    2:s3[received/3]<=lookup_sample>>>2;
                endcase
                received<=received+1;
            end
            case(stage)
            28: for(i=0;i<8;i=i+1)
                harmonics[i] <= ((tone==0 ? ($signed(s2[i])>>>3) : ($signed(s2[i])>>>1)) +
                                (tone==0 ? ($signed(s3[i])>>>4) : ($signed(s3[i])>>>2))) * $signed({1'b0,bright_smooth});
            29: for(i=0;i<8;i=i+1) waveval[i]<=$signed(s1[i])+($signed(harmonics[i])>>>8);
            30: for(i=0;i<8;i=i+1) enveloped[i]<=$signed(waveval[i])*$signed({1'b0,env[i]});
            31: for(i=0;i<8;i=i+1) with_velocity[i]<=($signed(enveloped[i])>>>16)*$signed({1'b0,vel[i]});
            32: for(i=0;i<4;i=i+1) pair[i]<=($signed(with_velocity[i*2])>>>7)+($signed(with_velocity[i*2+1])>>>7);
            33: total<=pair[0]+pair[1]+pair[2]+pair[3];
            34: gained<=($signed(total)>>>3)*$signed({1'b0,volume_smooth});
            35: if(($signed(gained)>>>7)>32767) sample<=32767;
               else if(($signed(gained)>>>7)<-32768) sample<=-32768;
               else sample<=$signed(gained)>>>7;
            endcase
        end
    end
endmodule
