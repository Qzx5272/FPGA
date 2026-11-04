// A quota bank with 32 independent note instances and its own synthesis lane.
module voice_bank #(parameter BANK_BITS=3,parameter BANK_ID=0)(
 input wire clk,rst,panic,sample_tick,event_valid,output wire event_ready,
 input wire [1:0] kind,input wire [7:0] source,contact,input wire [3:0] part,
 input wire [31:0] epoch,serial,input wire [6:0] note,velocity,
 output wire valid_out,output wire signed [15:0] sample_out,
 output wire [15:0] voices,cycles,output wire [31:0] rejected,deadline,clips,
 input wire control_valid,input wire [3:0] control_part,input wire [3:0] control_parameter,input wire [13:0] control_value
);
 wire [4:0] query,retire_slot;wire active,gate,retire;wire [6:0] qnote,qvelocity;
 wire [3:0] qpart;wire [31:0] generation,retire_generation,stale,duplicates;wire done,exhausted;
 localparam PARTS=16>>BANK_BITS;
 wire [3:0] parameter_index=control_part>>BANK_BITS,query_index=qpart>>BANK_BITS,release_index=part>>BANK_BITS;
 reg [7:0] expression[0:PARTS-1],target_expression[0:PARTS-1],bend[0:PARTS-1],target_bend[0:PARTS-1];
 reg [2:0] vowel[0:PARTS-1];
 reg [15:0] attack[0:PARTS-1],sustain[0:PARTS-1];reg [3:0] decay[0:PARTS-1],release_rate[0:PARTS-1];integer i;
 always @(posedge clk)begin
  if(rst)for(i=0;i<PARTS;i=i+1)begin expression[i]<=128;target_expression[i]<=128;bend[i]<=128;target_bend[i]<=128;vowel[i]<=0;attack[i]<=((i<<BANK_BITS)|BANK_ID)>=5?256:8192;sustain[i]<=((i<<BANK_BITS)|BANK_ID)>=5?65535:0;decay[i]<=13;release_rate[i]<=8;end
  else begin
   if(sample_tick)for(i=0;i<PARTS;i=i+1)begin
    if(expression[i]<target_expression[i])expression[i]<=expression[i]+1'b1;
    else if(expression[i]>target_expression[i])expression[i]<=expression[i]-1'b1;
    if(bend[i]<target_bend[i])bend[i]<=bend[i]+1'b1;
    else if(bend[i]>target_bend[i])bend[i]<=bend[i]-1'b1;
   end
   if(control_valid)case(control_parameter)
    0:target_expression[parameter_index]<=control_value>=127?8'd128:{1'b0,control_value[6:0]};
    1:target_bend[parameter_index]<=control_value[13:6];
    2:if(control_value<=4)vowel[parameter_index]<=control_value[2:0];
    4:attack[parameter_index]<=control_value==0?16'd1:{2'd0,control_value};
    5:decay[parameter_index]<=control_value[3:0];
    6:sustain[parameter_index]<={control_value,2'd0};
    7:release_rate[parameter_index]<=control_value[3:0];
   endcase
   if(event_valid&&event_ready&&kind==3)begin target_expression[release_index]<=128;target_bend[release_index]<=128;end
  end
 end
 note_allocator allocator(clk,rst,panic,event_valid,event_ready,kind,source,contact,part,epoch,serial,note,velocity,
  retire,retire_slot,retire_generation,query,active,gate,qnote,qvelocity,qpart,generation,done,rejected,stale,duplicates,exhausted);
 band_renderer #(.ENABLE_CHOIR((7&((1<<BANK_BITS)-1))==BANK_ID)) renderer(clk,rst,panic,sample_tick,query,active,gate,qnote,qvelocity,qpart,generation,
  retire,retire_slot,retire_generation,valid_out,sample_out,deadline,clips,cycles,voices,expression[query_index],bend[query_index],vowel[query_index],
  attack[query_index],decay[query_index],sustain[query_index],release_rate[query_index]);
endmodule
