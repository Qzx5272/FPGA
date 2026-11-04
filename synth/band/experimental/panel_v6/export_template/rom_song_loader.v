// Persistent on-chip event songs -> existing atomic RAM score uploader.
// Source1 internal conductor. No PCM and no host streaming after selection.
module rom_song_loader #(parameter TIMEOUT_CYCLES=32'd1500000000)(
 input wire clk,rst,request,input wire[7:0]selection,
 input wire upload_pending,uploading,input wire[31:0]upload_errors,
 output wire valid,input wire ready,output reg[223:0]payload,
 output wire busy,output reg failed,output reg[7:0]current_song);
 `include "song_library_config.vh"
 reg[31:0]rom[0:LIBRARY_WORDS-1];initial $readmemh("song_library_words.mem",rom);
 reg[31:0]rom_data;reg[15:0]base,index;reg[31:0]word_held,words,duration,checksum,error_baseline;
 reg[3:0]state;reg[31:0]timeout;
 wire[127:0]description=library_description(selection);
 always @(posedge clk)rom_data<=rom[base+index];
 assign busy=state!=0;assign valid=state==1||state==2||state==5||state==6||state==8||state==9||state==10||state==11;
 always @*begin
  payload=224'd0;payload[7:0]=4;payload[23:16]=1;payload[47:40]=60;payload[55:48]=100;
  case(state)
  1:begin payload[15:8]=5;payload[63:56]=1;end
  2:begin payload[15:8]=13;payload[63:56]=3;payload[95:64]=words/3;payload[127:96]=duration;payload[223:192]=checksum;end
  5:begin payload[15:8]=13;payload[63:56]=index%3;payload[95:64]=index/3;payload[127:96]=word_held;end
  6:begin payload[15:8]=13;payload[63:56]=4;end
  8:begin payload[15:8]=5;payload[63:56]=0;end
  9:begin payload[15:8]=13;payload[63:56]=5;end
  10:begin payload[15:8]=5;payload[63:56]=1;end
  11:begin payload[15:8]=5;payload[63:56]=0;end
  default:begin end
  endcase
 end
 always @(posedge clk)begin
  if(rst)begin state<=0;index<=0;base<=0;words<=0;duration<=0;checksum<=0;error_baseline<=0;timeout<=0;failed<=0;current_song<=0;word_held<=0;end
  else begin
   if(state!=0&&state<9)begin
    timeout<=timeout+1'b1;
   end
   case(state)
   0:if(request)begin
    if(selection>=LIBRARY_SONGS||uploading)failed<=1;
    else begin
     base<=description[111:96];words<=description[95:64];
     duration<=description[63:32];checksum<=description[31:0];
     current_song<=selection;index<=0;error_baseline<=upload_errors;timeout<=0;failed<=0;state<=1;
    end
   end
   1:if(ready)state<=2;
   2:if(ready)state<=3;
   3:state<=4;
   4:begin word_held<=rom_data;state<=5;end
   5:if(ready)begin if(index+1>=words)state<=6;else begin index<=index+1'b1;state<=3;end end
   6:if(ready)state<=7;
   7:if(upload_pending)state<=8;
   8:if(ready)state<=0;
   9,10,11:begin end
   default:state<=0;
   endcase
   // Failure has priority over ordinary state advancement.
   if(state!=0&&state<9&&(timeout>=TIMEOUT_CYCLES||upload_errors!=error_baseline))begin failed<=1;state<=9;end
   if(state==9&&ready)state<=10;
   else if(state==10&&ready)state<=11;
   else if(state==11&&ready)state<=0;
  end
 end
endmodule
