// Eight physical encoders -> ready/valid V4 command payload. No pin assumptions.
// 0 master,1 tempo,2 expression,3 role,4 attack,5 release,6 delay,7 choir vowel.
// Dirty parameters coalesce; a backpressured output is held unchanged.
module panel_controls #(parameter DEBOUNCE=25000)(
 input wire clk,rst,input wire[7:0] enc_a,enc_b,
 output reg valid,input wire ready,output reg[223:0] payload,
 output reg[3:0] selected_part,output wire[111:0] values
);
 wire[7:0] up,down;
 reg[13:0] value[0:7];reg[7:0] dirty;
 reg[2:0] cursor;
 wire[31:0] errors[0:7];
 genvar n;generate for(n=0;n<8;n=n+1)begin:knob
  quadrature_encoder #(.STABLE_CYCLES(DEBOUNCE)) decoder(clk,rst,enc_a[n],enc_b[n],up[n],down[n],errors[n]);
  assign values[n*14+:14]=value[n];
 end endgenerate
 integer i,index;reg found;reg[2:0] choice;reg[13:0] lo,hi,step;
 reg[223:0] command;
 always @*begin
  found=0;choice=cursor;
  for(i=0;i<8;i=i+1)begin
   index=(cursor+i)&7;
   if(!found&&dirty[index])begin found=1;choice=index;end
  end
  command=224'd0;command[7:0]=4;command[23:16]=1;command[27:24]=selected_part;
  case(choice)
   0:begin command[15:8]=10;command[205:192]=value[0];end
   1:begin command[15:8]=15;command[205:192]=value[1];end
   2:begin command[15:8]=11;command[63:56]=0;command[205:192]=value[2];end
   4:begin command[15:8]=11;command[63:56]=4;command[205:192]=value[4];end
   5:begin command[15:8]=11;command[63:56]=7;command[205:192]=value[5];end
   6:begin command[15:8]=7;command[205:192]=value[6];end
   7:begin command[15:8]=11;command[27:24]=7;command[63:56]=2;command[205:192]=value[7];end
   default:begin command[15:8]=6;end
  endcase
 end
 always @(posedge clk)begin
  if(rst)begin
   valid<=0;payload<=0;selected_part<=6;dirty<=0;cursor<=0;
   value[0]<=64;value[1]<=120;value[2]<=127;value[3]<=6;
   value[4]<=256;value[5]<=8;value[6]<=24;value[7]<=0;
  end else begin
   if(valid&&ready)valid<=0;
   if((!valid||ready)&&found)begin
    dirty[choice]<=0;cursor<=choice+1'b1;
    if(choice!=3)begin payload<=command;valid<=1;end
   end
   // Input updates win over clearing dirty on the same clock.
   for(i=0;i<8;i=i+1)if(up[i]||down[i])begin
    lo=i==1?40:i==4?1:0;hi=i==1?240:i==3?14:i==4?16383:i==5?15:i==7?4:127;
    step=i==4?64:1;
    if(up[i])value[i]<=value[i]>=hi-step?hi:value[i]+step;
    else value[i]<=value[i]<=lo+step?lo:value[i]-step;
    if(i!=3)dirty[i]<=1;
    else begin
     selected_part<=up[i]?(value[i]>=14?14:value[i]+1'b1):(value[i]==0?0:value[i]-1'b1);
     dirty[2]<=1;dirty[4]<=1;dirty[5]<=1;
    end
   end
  end
 end
endmodule
