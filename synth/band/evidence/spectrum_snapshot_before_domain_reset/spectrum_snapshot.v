// Freeze a complete FFT frame for a separately clocked display/host reader.
// Backpressure applies to analysis only; never connect this ready to audio.
// Metadata is bundled with the publish toggle and held through acknowledgement.
module spectrum_snapshot #(parameter LOG_N=11)(
 input analysis_clk,display_clk,rst,
 input bin_valid,output bin_ready,input[LOG_N-1:0]bin_index,
 input signed[15:0]bin_real,bin_imag,input[31:0]input_frame,input_last_sample,
 input[16:0]input_peak_left,input_peak_right,
 input read_enable,input[LOG_N-1:0]read_address,input release_frame,
 output reg frame_available,read_valid,output reg signed[15:0]read_real,read_imag,
 output reg[31:0]frame_number,last_sample,output reg[16:0]peak_left,peak_right,
 output reg[31:0]rejected_bins
);
 localparam LAST=(1<<LOG_N)-1;
 reg[31:0]memory[0:LAST];reg[LOG_N-1:0]expected;
 reg busy,publish,ack,seen;
 (* ASYNC_REG="TRUE" *)reg ack1,ack2,pub1,pub2;
 reg[31:0]stored_frame,stored_last;reg[16:0]stored_left,stored_right;
 assign bin_ready=!rst&&!busy;
 wire metadata_matches=input_frame==stored_frame&&input_last_sample==stored_last&&
  input_peak_left==stored_left&&input_peak_right==stored_right;
 wire accepted=bin_valid&&bin_ready&&bin_index==expected&&(expected==0||metadata_matches);
 always @(posedge analysis_clk)if(accepted)memory[bin_index]<={bin_real,bin_imag};
 always @(posedge display_clk)if(!rst&&frame_available&&read_enable&&!release_frame)
  {read_real,read_imag}<=memory[read_address];
 always @(posedge analysis_clk or posedge rst)begin
  if(rst)begin
   expected<=0;busy<=0;publish<=0;ack1<=0;ack2<=0;rejected_bins<=0;
   stored_frame<=0;stored_last<=0;stored_left<=0;stored_right<=0;
  end else begin
   ack1<=ack;ack2<=ack1;
   if(busy)begin if(ack2==publish)begin busy<=0;expected<=0;end end
   else if(bin_valid)begin
    if(accepted)begin
     if(expected==0)begin stored_frame<=input_frame;stored_last<=input_last_sample;
      stored_left<=input_peak_left;stored_right<=input_peak_right;end
     if(expected==LAST)begin busy<=1;publish<=!publish;end
     else expected<=expected+1'b1;
    end else begin
     expected<=0;if(rejected_bins!=32'hffffffff)rejected_bins<=rejected_bins+1'b1;
    end
   end
  end
 end
 always @(posedge display_clk or posedge rst)begin
  if(rst)begin
   pub1<=0;pub2<=0;seen<=0;ack<=0;frame_available<=0;read_valid<=0;
   frame_number<=0;last_sample<=0;peak_left<=0;peak_right<=0;
  end else begin
   pub1<=publish;pub2<=pub1;
   read_valid<=frame_available&&read_enable&&!release_frame;
   if(frame_available&&release_frame)begin frame_available<=0;ack<=seen;end
   else if(!frame_available&&pub2!=seen)begin
    seen<=pub2;frame_available<=1;frame_number<=stored_frame;last_sample<=stored_last;
    peak_left<=stored_left;peak_right<=stored_right;
   end
  end
 end
endmodule
