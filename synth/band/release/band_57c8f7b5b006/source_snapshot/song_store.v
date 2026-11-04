`include "song_config.vh"
// Double-buffered event storage. Upload never writes the currently playing bank.
// Commands 0/1/2 write control/identity/timestamp; 3 begin; 4 validate commit.
module song_store(
 input wire clk,rst,abort_upload,activate,
 input wire [11:0] read_address,output reg [95:0] read_data,
 output reg [12:0] event_count,output reg [31:0] duration,
 input wire upload_valid,output wire upload_ready,input wire [2:0] upload_command,
 input wire [31:0] upload_index,upload_value,upload_aux,
 output reg pending,output reg uploading,output reg [12:0] received_entries,
 output reg [1:0] expected_word,output reg [31:0] errors
);
 reg [31:0] controls[0:8191],identities[0:8191],times[0:8191];
 initial begin
  `include "song_storage_init.vh"
 end
 reg active_bank,upload_bank;reg [12:0] new_count;reg [31:0] new_duration,expected_crc,crc,last_time;
 reg busy;reg [1:0] byte_index;reg [31:0] word;
 wire [12:0] write_address={upload_bank,upload_index[11:0]};
 assign upload_ready=!busy&&!activate&&!abort_upload;
 function [31:0] crc_byte;
 input [31:0] old;input [7:0] b;reg [31:0] c;integer i;
 begin c=old^{24'd0,b};for(i=0;i<8;i=i+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;crc_byte=c;end
 endfunction
 always @(posedge clk)read_data<={times[{active_bank,read_address}],identities[{active_bank,read_address}],controls[{active_bank,read_address}]};
 wire data_command=upload_command<3;
 wire ordered=upload_index==received_entries&&upload_command[1:0]==expected_word&&received_entries<new_count;
 wire semantic_ok=upload_command==0 ? (upload_value[31:20]==0&&((!upload_value[1]&&(upload_value[0]||upload_value[19:13]!=0))||(upload_value[1:0]==2&&upload_value[12:6]<=4&&upload_value[19:13]==0))):
                  upload_command==1 ? upload_value!=0 : upload_value>=last_time&&upload_value<new_duration;
 wire accept_word=upload_valid&&upload_ready&&uploading&&data_command&&ordered&&semantic_ok;
 // Single write port on each banked array; no clearing that would destroy RAM inference.
 always @(posedge clk)begin
  if(accept_word&&upload_command==0)controls[write_address]<=upload_value;
  if(accept_word&&upload_command==1)identities[write_address]<=upload_value;
  if(accept_word&&upload_command==2)times[write_address]<=upload_value;
 end
 always @(posedge clk)begin
  if(rst)begin
   active_bank<=0;upload_bank<=1;event_count<=`SONG_EVENTS;duration<=`SONG_LENGTH;
   pending<=0;uploading<=0;received_entries<=0;expected_word<=0;errors<=0;busy<=0;crc<=32'hffffffff;
   new_count<=0;new_duration<=0;expected_crc<=0;last_time<=0;word<=0;byte_index<=0;
  end else if(abort_upload)begin uploading<=0;busy<=0;end
  else begin
   if(activate&&pending)begin active_bank<=upload_bank;event_count<=new_count;duration<=new_duration;pending<=0;end
   if(busy)begin
    crc<=crc_byte(crc,word[byte_index*8+:8]);
    if(byte_index==3)begin
     busy<=0;
     if(expected_word==2)begin expected_word<=0;received_entries<=received_entries+1'b1;end
     else expected_word<=expected_word+1'b1;
    end else byte_index<=byte_index+1'b1;
   end
   if(upload_valid&&upload_ready)begin
    if(upload_command==3)begin
     if(upload_index==0||upload_index>4096||upload_value==0||upload_value[31])begin errors<=errors+1'b1;uploading<=0;end
     else begin
      upload_bank<=~active_bank;new_count<=upload_index[12:0];new_duration<=upload_value;expected_crc<=upload_aux;
      crc<=32'hffffffff;last_time<=0;received_entries<=0;expected_word<=0;uploading<=1;pending<=0;
     end
    end else if(upload_command==5)begin uploading<=0;pending<=0;end
    else if(upload_command==4)begin
     if(uploading&&received_entries==new_count&&expected_word==0&&~crc==expected_crc)begin pending<=1;uploading<=0;end
     else begin errors<=errors+1'b1;uploading<=0;end
    end else if(accept_word)begin word<=upload_value;byte_index<=0;busy<=1;if(upload_command==2)last_time<=upload_value;end
    else begin errors<=errors+1'b1;uploading<=0;end
   end
  end
 end
endmodule
