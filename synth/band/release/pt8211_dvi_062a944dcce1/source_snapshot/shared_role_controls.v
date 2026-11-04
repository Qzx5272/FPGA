// One authoritative patch/slew state per musical role, shared by every bank.
// Payload layout per role: expression8,bend8,vowel3,attack16,sustain16,decay4,release4.
module shared_role_controls(
 input wire clk,rst,sample_tick,
 input wire control_valid,input wire [3:0] control_part,control_parameter,
 input wire [13:0] control_value,
 input wire release_valid,input wire [3:0] release_part,
 output wire [16*59-1:0] patches
);
 reg [7:0] expression[0:15],target_expression[0:15],bend[0:15],target_bend[0:15];
 reg [2:0] vowel[0:15];
 reg [15:0] attack[0:15],sustain[0:15];
 reg [3:0] decay[0:15],release_rate[0:15];
 genvar p;generate for(p=0;p<16;p=p+1)begin:pack
  assign patches[p*59+:59]={expression[p],bend[p],vowel[p],attack[p],sustain[p],decay[p],release_rate[p]};
 end endgenerate
 integer i;
 always @(posedge clk)begin
  if(rst)for(i=0;i<16;i=i+1)begin
   expression[i]<=128;target_expression[i]<=128;bend[i]<=128;target_bend[i]<=128;
   vowel[i]<=0;attack[i]<=i>=5?256:8192;sustain[i]<=i>=5?65535:0;decay[i]<=13;release_rate[i]<=8;
  end else begin
   if(sample_tick)for(i=0;i<16;i=i+1)begin
    if(expression[i]<target_expression[i])expression[i]<=expression[i]+1'b1;
    else if(expression[i]>target_expression[i])expression[i]<=expression[i]-1'b1;
    if(bend[i]<target_bend[i])bend[i]<=bend[i]+1'b1;
    else if(bend[i]>target_bend[i])bend[i]<=bend[i]-1'b1;
   end
   if(control_valid)case(control_parameter)
    0:target_expression[control_part]<=control_value>=127?8'd128:{1'b0,control_value[6:0]};
    1:target_bend[control_part]<=control_value[13:6];
    2:if(control_value<=4)vowel[control_part]<=control_value[2:0];
    4:attack[control_part]<=control_value==0?16'd1:{2'd0,control_value};
    5:decay[control_part]<=control_value[3:0];
    6:sustain[control_part]<={control_value,2'd0};
    7:release_rate[control_part]<=control_value[3:0];
   endcase
   // Same priority as the previous per-bank state: part release wins over a
   // coincident expression/bend target write; note tails keep their identity.
   if(release_valid)begin target_expression[release_part]<=128;target_bend[release_part]<=128;end
  end
 end
endmodule
