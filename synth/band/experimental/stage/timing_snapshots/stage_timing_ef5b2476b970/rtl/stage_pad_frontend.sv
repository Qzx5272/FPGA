// Experimental pipelined local calibration;original production pad_frontend unchanged.
// Calibrated local pressure input with separate release-priority event service.
// CHIPS 0..7 are 64 pads; remaining ADC lanes are continuous controls.
module stage_pad_frontend #(parameter CHIPS=10,parameter PADS=64)(
 input wire clk,rst,panic,input wire sample_valid,input wire [2:0] sample_channel,
 input wire [CHIPS*12-1:0] samples,
 input wire config_valid,input wire [6:0] config_channel,input wire [11:0] config_baseline,
 input wire [15:0] config_gain,input wire config_invert,
 input wire [6:0] on_threshold,off_threshold,
 output reg event_valid,input wire event_ready,output reg event_off,
 output reg [6:0] event_contact,event_pressure,output reg [31:0] event_serial,
 output reg [CHIPS*8*7-1:0] pressure_values,
 output reg [31:0] overruns,output reg exhausted
);
 localparam CHANNELS=CHIPS*8;
 reg [11:0] baselines[0:CHANNELS-1];reg [15:0] gains[0:CHANNELS-1];reg [CHANNELS-1:0] inversions;
 reg [PADS-1:0] physical,sent,inhibited;reg [31:0] serials[0:PADS-1],sent_serials[0:PADS-1];
 reg [CHIPS*12-1:0] batch;reg [2:0] channel;reg [3:0] lane;reg busy;
 wire [6:0] address={lane,channel};
 // Four cycles per ADC lane:lookup,subtract,multiply,apply.
 reg[1:0] phase;
 reg[11:0] raw_stage,baseline_stage,difference_stage;
 reg[15:0] gain_stage;reg invert_stage;reg[27:0] scaled_stage;
 wire[11:0] oriented=invert_stage?12'd4095-raw_stage:raw_stage;
 wire[6:0] pressure=scaled_stage[27:12]>127?7'd127:scaled_stage[18:12];
 integer i;reg found;reg chosen_off;reg [6:0] chosen;
 always @*begin
  found=0;chosen=0;chosen_off=0;
  for(i=0;i<PADS;i=i+1)if(!found&&sent[i]&&(!physical[i]||sent_serials[i]!=serials[i]))begin chosen=i;chosen_off=1;found=1;end
  for(i=0;i<PADS;i=i+1)if(!found&&!sent[i]&&physical[i])begin chosen=i;chosen_off=0;found=1;end
 end
 integer k;
 always @(posedge clk)begin
  if(rst)begin
   physical<=0;sent<=0;inhibited<={PADS{1'b1}};inversions<=0;busy<=0;event_valid<=0;pressure_values<=0;overruns<=0;exhausted<=0;phase<=0;raw_stage<=0;baseline_stage<=0;difference_stage<=0;gain_stage<=0;invert_stage<=0;scaled_stage<=0;
   for(k=0;k<CHANNELS;k=k+1)begin baselines[k]<=0;gains[k]<=127;end
   for(k=0;k<PADS;k=k+1)begin serials[k]<=0;sent_serials[k]<=0;end
  end else if(panic)begin physical<=0;sent<=0;inhibited<={PADS{1'b1}};event_valid<=0;busy<=0;phase<=0;end
  else begin
   if(config_valid&&config_channel<CHANNELS)begin
    baselines[config_channel]<=config_baseline;gains[config_channel]<=config_gain;inversions[config_channel]<=config_invert;
   end
   if(sample_valid)begin
    if(busy)overruns<=overruns+1'b1;
    else begin batch<=samples;channel<=sample_channel;lane<=0;busy<=1;phase<=0;end
   end
   if(busy)case(phase)
    0:begin raw_stage<=batch[lane*12+:12];baseline_stage<=baselines[address];gain_stage<=gains[address];invert_stage<=inversions[address];phase<=1;end
    1:begin difference_stage<=oriented>baseline_stage?oriented-baseline_stage:12'd0;phase<=2;end
    2:begin scaled_stage<=difference_stage*gain_stage;phase<=3;end
    3:begin
    pressure_values[address*7+:7]<=pressure;
    if(address<PADS)begin
     if(pressure<=off_threshold)begin physical[address]<=0;inhibited[address]<=0;end
     else if(pressure>=on_threshold&&!physical[address]&&!inhibited[address])begin
      if(serials[address]==32'hffffffff)begin exhausted<=1;inhibited[address]<=1;end
      else begin physical[address]<=1;serials[address]<=serials[address]+1'b1;end
     end
    end
    if(lane==CHIPS-1)busy<=0;else lane<=lane+1'b1;phase<=0;
    end
   endcase
   if(event_valid&&event_ready)begin
    event_valid<=0;
    if(event_off)sent[event_contact]<=0;
    else begin sent[event_contact]<=1;sent_serials[event_contact]<=event_serial;end
   end else if(!event_valid&&found)begin
    event_valid<=1;event_contact<=chosen;event_off<=chosen_off;
    event_pressure<=pressure_values[chosen*7+:7];event_serial<=chosen_off?sent_serials[chosen]:serials[chosen];
   end
  end
 end
endmodule
