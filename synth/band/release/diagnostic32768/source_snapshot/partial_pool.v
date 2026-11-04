// Diagnostic throughput profile, intentionally separate from the band renderer.
module partial_pool #(parameter LANE_BITS=3,parameter ADDRESS_BITS=9)(
 input wire clk,rst,start,config_valid,
 input wire [LANE_BITS+ADDRESS_BITS-1:0] config_address,
 input wire [31:0] config_phase,config_increment,
 input wire [15:0] config_envelope,config_target,config_slew,
 output wire config_ready,initialized,
 output reg valid_out,output reg signed [23:0] sample_out,
 output reg [15:0] active_count,last_cycles,output reg [31:0] deadline_miss
);
 localparam LANES=1<<LANE_BITS;
 wire [LANES-1:0] readies,inits,dones;
 wire signed [31:0] sums[0:LANES-1];
 wire [15:0] counts[0:LANES-1];wire [31:0] misses[0:LANES-1];
 reg running;reg [15:0] cycles;
 reg signed [39:0] combined;reg [16:0] count_combined;
 integer j;
 assign config_ready=&readies;assign initialized=&inits;
 genvar lane;
 generate for(lane=0;lane<LANES;lane=lane+1)begin:bank
  partial_lane #(.ADDRESS_BITS(ADDRESS_BITS)) core(
   clk,rst,start,config_valid&&config_ready&&(config_address[LANE_BITS+ADDRESS_BITS-1:ADDRESS_BITS]==lane),
   config_address[ADDRESS_BITS-1:0],config_phase,config_increment,config_envelope,config_target,config_slew,
   readies[lane],inits[lane],dones[lane],sums[lane],counts[lane],misses[lane]);
 end endgenerate
 always @*begin
  combined=0;count_combined=0;
  for(j=0;j<LANES;j=j+1)begin combined=combined+$signed(sums[j]);count_combined=count_combined+counts[j];end
 end
 always @(posedge clk)begin
  if(rst)begin valid_out<=0;sample_out<=0;active_count<=0;last_cycles<=0;deadline_miss<=0;running<=0;cycles<=0;end
  else begin
   valid_out<=0;
   if(start&&initialized)begin
    if(running)deadline_miss<=deadline_miss+1'b1;
    else begin running<=1;cycles<=0;end
   end
   if(running)cycles<=cycles+1'b1;
   if(&dones)begin
    sample_out<=combined>>>(LANE_BITS+ADDRESS_BITS-6);
    active_count<=count_combined[15:0];last_cycles<=cycles;valid_out<=1;running<=0;
   end
  end
 end
endmodule
