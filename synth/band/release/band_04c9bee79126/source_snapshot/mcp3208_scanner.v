// Parallel MCP3208 chips: common CS/CLK/DIN, separate DOUT per chip.
// 50 MHz defaults: SCLK=757575.76 Hz; 32 clocks + 640 ns CS-high per conversion.
// Each of eight channels is sampled at 50e6/(8*(32*66+32)) = 2915.11 Hz.
// Datasheet DS21298E Fig 6-1, mode 0, leading zeros, final 12 returned bits.
module mcp3208_scanner #(parameter CHIPS=10,parameter HALF_PERIOD=33,parameter CS_GAP=32)(
 input wire clk,rst,input wire [CHIPS-1:0] dout,
 output reg cs_n,sclk,din,output reg sample_valid,
 output reg [2:0] sample_channel,output reg [CHIPS*12-1:0] samples
);
 reg [15:0] divider;reg [5:0] bit_index;reg [2:0] channel;
 reg [31:0] command_word;reg [31:0] received[0:CHIPS-1];
 reg [CHIPS-1:0] sync0,sync1;
 integer i;
 always @(posedge clk)begin
  sync0<=dout;sync1<=sync0;
  if(rst)begin
   cs_n<=1;sclk<=0;din<=0;sample_valid<=0;sample_channel<=0;samples<=0;
   divider<=CS_GAP-1;bit_index<=31;channel<=0;command_word<=0;
   for(i=0;i<CHIPS;i=i+1)received[i]<=0;
  end else begin
   sample_valid<=0;
   if(divider!=0)divider<=divider-1'b1;
   else if(cs_n)begin
    cs_n<=0;sclk<=0;din<=0;bit_index<=31;divider<=HALF_PERIOD-1;
    command_word<=32'h00060000|({29'd0,channel}<<14);
   end else begin
    divider<=HALF_PERIOD-1;sclk<=~sclk;
    if(!sclk)for(i=0;i<CHIPS;i=i+1)received[i]<={received[i][30:0],sync1[i]};
    else if(bit_index==0)begin
     cs_n<=1;sclk<=0;din<=0;divider<=CS_GAP-1;sample_valid<=1;sample_channel<=channel;channel<=channel+1'b1;
     for(i=0;i<CHIPS;i=i+1)samples[i*12+:12]<=received[i][11:0];
    end else begin bit_index<=bit_index-1'b1;din<=command_word[bit_index-1'b1];end
   end
  end
 end
endmodule
