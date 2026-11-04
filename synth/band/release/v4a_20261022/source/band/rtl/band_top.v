// Board audition build: existing, verified PT8211 pins only. Not standard-I2S acceptance.
module band_top(input clk,input uart_rx_pin,output uart_tx_pin,
 output HP_BCK,HP_WS,HP_DIN,output PA_EN);
 reg [15:0] startup=0;always @(posedge clk)if(!(&startup))startup<=startup+1'b1;
 wire rst=!(&startup);
 wire [7:0] byte_data;wire byte_valid;
 uart_rx #(.DIV(50)) rx(clk,rst,uart_rx_pin,byte_data,byte_valid);
 wire packet_valid,packet_ready,panic;wire [223:0] packet;wire [31:0] crc_errors,overflow;
 event_receiver receiver(clk,rst,byte_data,byte_valid,packet_valid,packet_ready,packet,panic,crc_errors,overflow);
 wire [7:0] kind=packet[15:8],source=packet[23:16];wire [3:0] part=packet[27:24];
 wire source_ok=source>=1&&source<=4;
 wire manual_ready,command_ready;
 wire is_manual=kind<4;
 wire is_command=kind==4;
 wire command_allowed=source_ok&&(packet[57:56]<2||source==1);
 assign packet_ready=!source_ok?1'b1:is_manual?manual_ready:is_command&&command_allowed?command_ready:1'b1;
 wire accepted=packet_valid&&packet_ready;
 reg [6:0] wet,master;reg [3:0] status_part;reg status_request;
 reg play,stop;
 wire sample_tick,playing,audio_valid;wire signed [15:0] left,right;
 wire [31:0] song_position,status_epoch,rejected,deadline_miss,clips,denied;
 wire [15:0] active_voices,render_cycles;wire [7:0] status_owner;
 reg [14:0] lease[1:4];reg [3:0] lost_pending;
 reg [7:0] lost_source;integer i;wire lost_ready;
 always @*begin
  if(lost_pending[0])lost_source=1;else if(lost_pending[1])lost_source=2;
  else if(lost_pending[2])lost_source=3;else lost_source=4;
 end
 always @(posedge clk)begin
  if(rst)begin wet<=32;master<=96;status_part<=0;status_request<=0;lost_pending<=0;play<=0;stop<=0;for(i=1;i<=4;i=i+1)lease[i]<=0;end
  else begin
   play<=accepted&&source_ok&&kind==5&&packet[63:56]==0;
   stop<=accepted&&source_ok&&kind==5&&packet[63:56]==1;
   status_request<=accepted;
   if(sample_tick)for(i=1;i<=4;i=i+1)if(lease[i]!=0)begin
    lease[i]<=lease[i]-1'b1;if(lease[i]==1)lost_pending[i-1]<=1;
   end
   if((|lost_pending)&&lost_ready)lost_pending[lost_source-1]<=0;
   if(accepted&&source_ok)begin
    lease[source]<=24000;status_part<=part;
    if(kind==7&&source==1)wet<=packet[198:192];
    if(kind==10&&source==1)master<=packet[198:192];
   end
  end
 end
 band_core core(clk,rst,panic,sample_tick,play,stop,
  packet_valid&&source_ok&&is_manual,manual_ready,kind[1:0],source,packet[39:32],part,
  packet[95:64],packet[127:96],packet[46:40],packet[54:48],
  packet_valid&&is_command&&command_allowed,command_ready,packet[57:56],part,source,wet,master,
  left,right,audio_valid,playing,song_position,status_part,status_owner,status_epoch,
  active_voices,render_cycles,rejected,deadline_miss,clips,denied,|lost_pending,lost_ready,lost_source);
 audio_serial #(.MODE_I2S(0)) dac(clk,rst,left,right,HP_BCK,HP_WS,HP_DIN,sample_tick);
 assign PA_EN=~rst;
 wire [223:0] status_snapshot={clips,deadline_miss,rejected,song_position,status_epoch,
  render_cycles,active_voices,{4'd0,status_part},status_owner,{7'b1000000,playing},8'd4};
 status_sender telemetry(clk,rst,status_request,status_snapshot,uart_tx_pin);
endmodule
