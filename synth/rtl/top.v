module top(input clk, input uart_rx_pin, output uart_tx_pin,
    output HP_BCK, HP_WS, HP_DIN, output PA_EN);
    reg [15:0] startup=0;
    always @(posedge clk) if(!(&startup)) startup<=startup+1;
    wire rst= !(&startup);
    wire [7:0] rx_data,keys,sequence,brightness;
    wire rx_valid,panic,packet_valid,online;
    wire [2:0] octave;
    wire [1:0] tone;
    wire [6:0] volume,velocity;
    wire [15:0] attack_step,release_step;
    wire signed [15:0] sample, instrument_sample, voice_sample, hello_sample;
    wire [3:0] voices, instrument_voices;
    wire voice_active,hello_active;
    wire hello_mode=tone==3 && (brightness==8 || brightness==9);
    wire signed [15:0] singer=hello_mode?hello_sample:voice_sample;
    wire signed [16:0] duet=$signed(instrument_sample)+$signed(singer);
    assign sample=tone==3 ? (auto_play ? (duet>>>1) : singer) : instrument_sample;
    assign voices=tone==3 ? ((auto_play?instrument_voices:4'd0)+(hello_mode?{3'b0,hello_active}:{3'b0,voice_active})) : instrument_voices;
    wire sample_tick;
    wire auto_play;
    wire [5:0] tempo_code;
    wire [7:0] auto_keys;
    wire [3:0] song_position;
    auto_accompaniment arranger(clk,rst,sample_tick,panic,auto_play,tempo_code,auto_keys,song_position);
    uart_rx receiver(clk,rst,uart_rx_pin,rx_data,rx_valid);
    control controls(clk,rst,rx_data,rx_valid,keys,sequence,brightness,octave,tone,volume,velocity,
                     attack_step,release_step,panic,packet_valid,online,auto_play,tempo_code);
    engine synth(clk,rst,sample_tick,panic||(tone==3&&!auto_play),
                 tone==3?auto_keys:(keys|auto_keys),tone==3?8'd80:brightness,octave,tone==3?2'd0:tone,volume,velocity,
                 attack_step,release_step,instrument_sample,instrument_voices);
    voice_engine human_voice(clk,rst,sample_tick,panic,tone==3&&!hello_mode,keys,octave,brightness[2:0],
                 volume,velocity,attack_step,release_step,voice_sample,voice_active);
    hello_engine greeting(clk,rst,sample_tick,panic,hello_mode,|keys,brightness==9,
                 volume,velocity,hello_sample,hello_active);
    audio_serial #(.MODE_I2S(0)) dac(clk,rst,sample,sample,HP_BCK,HP_WS,HP_DIN,sample_tick);
    // Headphone amplifier enable; default digital silence until valid controls arrive.
    assign PA_EN=~rst;
    reg [15:0] peak;
    wire [15:0] magnitude=sample[15] ? -sample : sample;
    always @(posedge clk) begin
        if(rst || packet_valid) peak<=0;
        else if(sample_tick && magnitude>peak) peak<=magnitude;
    end
    telemetry feedback(clk,rst,packet_valid,online,sequence,keys,voices,peak,uart_tx_pin);
endmodule
