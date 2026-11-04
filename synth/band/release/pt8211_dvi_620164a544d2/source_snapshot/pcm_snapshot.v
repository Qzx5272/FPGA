// Real synthesized PCM -> frozen display/analysis window. No audio ready signal:
// a slow/stopped reader drops visualization samples, never stalls synthesis.
// Both domains share reset. Metadata is bundled with publish_toggle and remains
// stable until reader release crosses back; board CDC constraints still required.
module pcm_snapshot #(parameter ADDRESS_BITS=9)(
 input audio_clk,read_clk,rst,pcm_valid,
 input signed[15:0] pcm_left,pcm_right,
 input read_enable,input[ADDRESS_BITS-1:0] read_address,input release_frame,
 output reg frame_available,read_valid,
 output reg signed[15:0] read_left,read_right,
 output reg[16:0] frame_peak_left,frame_peak_right,
 output reg[31:0] frame_last_sample,frame_number,
 output reg[31:0] visualization_skipped
);
 // Common asynchronous assertion; release independently in each clock domain.
 (* ASYNC_REG="TRUE" *) reg[1:0]write_reset_hold=2'b11,read_reset_hold=2'b11;
 always @(posedge audio_clk or posedge rst)
  if(rst)write_reset_hold<=2'b11;else write_reset_hold<={write_reset_hold[0],1'b0};
 always @(posedge read_clk or posedge rst)
  if(rst)read_reset_hold<=2'b11;else read_reset_hold<={read_reset_hold[0],1'b0};
 wire write_reset=rst||write_reset_hold[1],read_reset=rst||read_reset_hold[1];
 localparam LAST=(1<<ADDRESS_BITS)-1;
 reg[31:0] samples[0:LAST];
 reg[ADDRESS_BITS-1:0] write_address;
 reg busy,publish_toggle,ack_toggle;
 (* ASYNC_REG="TRUE" *) reg ack_sync1,ack_sync2,pub_sync1,pub_sync2;
 reg seen;
 reg[16:0] peak_left,peak_right,published_left,published_right;
 reg[31:0] sample_count,published_last,published_number;
 wire[16:0] magnitude_left=pcm_left[15]?-$signed({pcm_left[15],pcm_left}):{1'b0,pcm_left};
 wire[16:0] magnitude_right=pcm_right[15]?-$signed({pcm_right[15],pcm_right}):{1'b0,pcm_right};
 wire[16:0] next_left=magnitude_left>peak_left?magnitude_left:peak_left;
 wire[16:0] next_right=magnitude_right>peak_right?magnitude_right:peak_right;
 // Separate write/read processes allow an inferred dual-clock block RAM.
 always @(posedge audio_clk)if(!write_reset&&pcm_valid&&!busy)samples[write_address]<={pcm_left,pcm_right};
 always @(posedge read_clk)if(!read_reset&&frame_available&&read_enable&&!release_frame)
  {read_left,read_right}<=samples[read_address];
 always @(posedge audio_clk or posedge write_reset)begin
  if(write_reset)begin
   ack_sync1<=0;ack_sync2<=0;busy<=0;publish_toggle<=0;write_address<=0;
   peak_left<=0;peak_right<=0;published_left<=0;published_right<=0;
   sample_count<=0;published_last<=0;published_number<=0;visualization_skipped<=0;
  end else begin
   ack_sync1<=ack_toggle;ack_sync2<=ack_sync1;
   if(pcm_valid)sample_count<=sample_count+1'b1;
   if(busy)begin
    if(pcm_valid&&visualization_skipped!=32'hffffffff)visualization_skipped<=visualization_skipped+1'b1;
    if(ack_sync2==publish_toggle)begin busy<=0;write_address<=0;peak_left<=0;peak_right<=0;end
   end else if(pcm_valid)begin
    peak_left<=next_left;peak_right<=next_right;
    if(write_address==LAST)begin
     published_left<=next_left;published_right<=next_right;published_last<=sample_count;
     published_number<=published_number+1'b1;publish_toggle<=!publish_toggle;busy<=1;
    end else write_address<=write_address+1'b1;
   end
  end
 end
 always @(posedge read_clk or posedge read_reset)begin
  if(read_reset)begin
   pub_sync1<=0;pub_sync2<=0;seen<=0;ack_toggle<=0;frame_available<=0;read_valid<=0;
   frame_peak_left<=0;frame_peak_right<=0;frame_last_sample<=0;frame_number<=0;
  end else begin
   pub_sync1<=publish_toggle;pub_sync2<=pub_sync1;
   read_valid<=frame_available&&read_enable&&!release_frame;
   if(frame_available&&release_frame)begin frame_available<=0;ack_toggle<=seen;end
   else if(!frame_available&&pub_sync2!=seen)begin
    seen<=pub_sync2;frame_available<=1;
    frame_peak_left<=published_left;frame_peak_right<=published_right;
    frame_last_sample<=published_last;frame_number<=published_number;
   end
  end
 end
endmodule
