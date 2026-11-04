// Independent partial diagnostic lane, one issue per clock.
// 112 state bits/partial: phase32, increment32, envelope16, target16, slew16.
// This is the measured-throughput profile, not the full V4 instrument state.
module partial_lane #(parameter ADDRESS_BITS=9)(
 input wire clk,rst,start,
 input wire config_valid,input wire [ADDRESS_BITS-1:0] config_address,
 input wire [31:0] config_phase,config_increment,
 input wire [15:0] config_envelope,config_target,config_slew,
 output wire config_ready,output reg initialized,done,
 output reg signed [31:0] sample_sum,output reg [15:0] active_count,
 output reg [31:0] deadline_miss
);
 localparam DEPTH=1<<ADDRESS_BITS;
 reg [31:0] phases[0:DEPTH-1],increments[0:DEPTH-1];
 reg [15:0] envelopes[0:DEPTH-1],targets[0:DEPTH-1],slews[0:DEPTH-1];
 reg [ADDRESS_BITS-1:0] clear_address,issue_address,address0;
 reg running,issuing,v0;
 reg [31:0] phase0,increment0;
 reg [15:0] envelope0,target0,slew0;
 reg [15:0] gain0,gain1,gain2,gain3;
 reg signed [34:0] product;
 reg product_valid;
 reg signed [31:0] sum;
 reg [ADDRESS_BITS:0] received;
 reg [15:0] active;
 wire [16:0] up={1'b0,envelope0}+{1'b0,slew0};
 wire [15:0] next_env=increment0==0?16'd0:
    envelope0<target0 ? (up>={1'b0,target0}?target0:up[15:0]):
    envelope0>target0 ? (envelope0-target0<=slew0?target0:envelope0-slew0):envelope0;
 wire sine_valid;wire signed [17:0] sine;
 hq_sine_quarter oscillator(clk,rst,v0,phase0,sine_valid,sine);
 assign config_ready=initialized&&!running&&!start;
 // Exactly one write port per array. Separate procedural writes for clear,
 // configure and feedback cause Gowin to implement the state in flip-flops.
 wire cfg_write=config_valid&&config_ready;
 wire state_write=!initialized||cfg_write||v0;
 wire parameter_write=!initialized||cfg_write;
 wire [ADDRESS_BITS-1:0] write_address=!initialized?clear_address:cfg_write?config_address:address0;
 wire [31:0] phase_write=!initialized?32'd0:cfg_write?config_phase:phase0+increment0;
 wire [15:0] envelope_write=!initialized?16'd0:cfg_write?config_envelope:next_env;
 always @(posedge clk)begin
  if(!rst)begin
   if(state_write)begin phases[write_address]<=phase_write;envelopes[write_address]<=envelope_write;end
   if(parameter_write)begin
    increments[write_address]<=!initialized?32'd0:config_increment;
    targets[write_address]<=!initialized?16'd0:config_target;
    slews[write_address]<=!initialized?16'd1:(config_slew==0?16'd1:config_slew);
   end
  end
 end
 always @(posedge clk)begin
  if(rst)begin
   initialized<=0;clear_address<=0;running<=0;issuing<=0;v0<=0;
   done<=0;sample_sum<=0;active_count<=0;deadline_miss<=0;product_valid<=0;
   sum<=0;received<=0;active<=0;
  end else begin
   done<=0;v0<=0;product_valid<=sine_valid;
   gain1<=gain0;gain2<=gain1;gain3<=gain2;
   if(!initialized)begin
    if(clear_address==DEPTH-1)initialized<=1;else clear_address<=clear_address+1'b1;
   end else begin
    if(start&&running)deadline_miss<=deadline_miss+1'b1;
    if(start&&!running)begin
     running<=1;issuing<=1;issue_address<=0;sum<=0;received<=0;active<=0;
    end
    if(issuing)begin
     phase0<=phases[issue_address];increment0<=increments[issue_address];
     envelope0<=envelopes[issue_address];target0<=targets[issue_address];slew0<=slews[issue_address];
     address0<=issue_address;v0<=1;
     if(issue_address==DEPTH-1)issuing<=0;else issue_address<=issue_address+1'b1;
    end
    if(v0)begin
     gain0<=next_env;
     if(next_env!=0&&increment0!=0)active<=active+1'b1;
    end
    if(sine_valid)product<=sine*$signed({1'b0,gain3});
    if(product_valid)begin
     sum<=sum+(product>>>16);received<=received+1'b1;
     if(received==DEPTH-1)begin
      sample_sum<=sum+(product>>>16);active_count<=active;done<=1;running<=0;
     end
    end
   end
  end
 end
endmodule
