// Single-voice algorithm probe, no CPU synthesis or sample skipping.
module v6_timbre_probe(input clk,rst,panic,tick,gate,input[3:0]part,input[6:0]note,
 input[15:0]attack,sustain,input[3:0]decay,release_rate,
 output valid,output signed[15:0]left,right,output[31:0]deadline,clips,output[15:0]cycles);
 wire query,retire;wire[31:0]retire_generation;wire[15:0]voices;
 shared_band_renderer #(.VOICES(1),.INDEX_BITS(1)) renderer(
 clk,rst,panic,tick,query,1'b1,gate,note,7'd100,part,32'd1,
 retire,,retire_generation,valid,left,deadline,clips,cycles,voices,
 8'd110,8'd128,3'd0,attack,decay,sustain,release_rate,right);
endmodule
