// Two independent ADC dimensions per role: chip 8 expression, chip 9 pitch/vowel.
// Startup pickup prevents unwired/untouched pots from muting the band. Only movement
// above 24 ADC counts publishes a control; pending updates coalesce by generation.
module local_expression(input wire clk,rst,panic,sample_valid,input wire [2:0] channel,
 input wire [119:0] samples,output reg valid,input wire ready,
 output reg [3:0] part,parameter_id,output reg [13:0] value);
 reg [7:0] initialized,pending;reg [11:0] previous[0:7],values[0:7];
 reg [15:0] generation[0:7],sent_generation;reg [2:0] selected;
 reg found;reg [2:0] chosen;integer j,k;reg [11:0] raw;reg [3:0] address;
 wire [14:0] vowel_product={3'd0,values[chosen]}*15'd5;
 always @*begin found=0;chosen=0;for(j=0;j<8;j=j+1)if(!found&&pending[j])begin found=1;chosen=j;end end
 always @(posedge clk)begin
  if(rst||panic)begin initialized<=0;pending<=0;valid<=0;for(k=0;k<8;k=k+1)generation[k]<=0;end
  else begin
   if(valid&&ready)begin valid<=0;if(generation[selected]==sent_generation)pending[selected]<=0;end
   else if(!valid&&found)begin
    selected<=chosen;sent_generation<=generation[chosen];valid<=1;
    case(chosen[1:0])0:part<=6;1:part<=3;2:part<=4;3:part<=7;endcase
    parameter_id<=chosen<4?0:chosen==7?2:1;
    value<=chosen<4?{7'd0,values[chosen][11:5]}:chosen==7?{11'd0,vowel_product[14:12]}:{values[chosen],2'd0};
   end
   if(sample_valid&&channel<4)for(k=0;k<2;k=k+1)begin
    address=k*4+channel;raw=samples[(8+k)*12+:12];
    if(!initialized[address])begin previous[address]<=raw;initialized[address]<=1;end
    else if((raw>previous[address]?raw-previous[address]:previous[address]-raw)>=24)begin
     previous[address]<=raw;values[address]<=raw;generation[address]<=generation[address]+1'b1;pending[address]<=1;
    end
   end
  end
 end
endmodule
