`define POOL_LANE_BITS 5
`ifndef POOL_LANE_BITS
`define POOL_LANE_BITS 3
`endif
// Dedicated independent-partial performance image. Not the band-performance image.
module diagnostic_top(input clk,input uart_rx_pin,output uart_tx_pin,
 output HP_BCK,HP_WS,HP_DIN,output PA_EN);
 localparam LB=`POOL_LANE_BITS;localparam IB=LB+9;localparam COUNT=1<<IB;
 reg [15:0] startup=0;always @(posedge clk)if(!(&startup))startup<=startup+1'b1;
 wire rst=!(&startup);wire [7:0] rx_data;wire rx_valid;
 uart_rx #(.DIV(50)) rx(clk,rst,uart_rx_pin,rx_data,rx_valid);
 wire packet_valid,packet_ready,panic;wire [223:0] packet;wire [31:0] errors,overflow;
 event_receiver receiver(clk,rst,rx_data,rx_valid,packet_valid,packet_ready,packet,panic,errors,overflow);
 wire [7:0] kind=packet[15:8];wire accepted=packet_valid&&packet_ready;
 wire config_ready,initialized,pool_valid,sample_tick;wire signed [23:0] pool_sample;
 wire [15:0] active_count,cycles;wire [31:0] deadline;
 reg playing,filling;reg [IB-1:0] address;reg [31:0] frame_count,rejected;
 wire legal_config=packet[95:64]<COUNT&&packet[127:96]<32'h80000000;
 wire config_request=packet_valid&&kind==9&&!filling&&legal_config;
 assign packet_ready=kind==9 ? (!filling&&config_ready):1'b1;
 wire [IB-1:0] configured_address=filling?address:packet[64+:IB];
 wire [31:0] frequency=filling?(50+(COUNT>8192?3:5)*address)*32'd32768:packet[127:96];
 wire [31:0] initial_phase=configured_address*32'h9e3779b9;
 partial_pool #(.LANE_BITS(LB)) pool(clk,rst||panic,sample_tick&&playing,
  filling||config_request,configured_address,initial_phase,frequency,
  filling?16'd0:packet[207:192],filling?16'd50000:packet[223:208],filling?16'd64:{8'd0,packet[63:56]},
  config_ready,initialized,pool_valid,pool_sample,active_count,cycles,deadline);
 always @(posedge clk)begin
  if(rst||panic)begin playing<=0;filling<=0;address<=0;frame_count<=0;rejected<=0;end
  else begin
   if(sample_tick&&playing)frame_count<=frame_count+1'b1;
   if(accepted&&kind==5)begin
    if(packet[63:56]==0)begin filling<=1;playing<=0;address<=0;frame_count<=0;end
    else begin playing<=0;filling<=0;end
   end else if(filling&&config_ready)begin
    if(address==COUNT-1)begin filling<=0;playing<=1;end else address<=address+1'b1;
   end
   if(accepted&&kind==9&&!legal_config)rejected<=rejected+1'b1;
  end
 end
 wire signed [15:0] monitor=playing?($signed(pool_sample)>>>11):16'd0;
 audio_serial #(.MODE_I2S(0)) dac(clk,rst,monitor,monitor,HP_BCK,HP_WS,HP_DIN,sample_tick);
 assign PA_EN=~rst;
 reg request;always @(posedge clk)if(rst)request<=0;else request<=accepted;
 wire [223:0] snapshot={32'd0,deadline,rejected,frame_count,32'd0,cycles,active_count,8'd0,8'd0,{7'b1001000,playing},8'd4};
 status_sender feedback(clk,rst,request,snapshot,uart_tx_pin);
endmodule
