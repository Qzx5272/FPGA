`include "song_config.vh"
// Autonomous event ROM score. No dependency on host timing after play.
module song_sequencer(
 input wire clk,rst,panic,sample_tick,play,stop,
 output reg playing,bar_tick,
 output reg event_valid,input wire event_ready,
 output wire [1:0] event_kind,output wire [3:0] event_part,
 output wire [6:0] event_note,event_velocity,output wire [31:0] event_serial,
 output reg [31:0] sample_position,late_events,
 output reg [7:0] bar_position,
 input wire upload_valid,output wire upload_ready,input wire [2:0] upload_command,
 input wire [31:0] upload_index,upload_value,upload_aux,
 output wire upload_pending,uploading,output wire [12:0] received_entries,
 output wire [1:0] expected_word,output wire [31:0] upload_errors,
 output wire [12:0] stored_events,output wire [31:0] stored_duration,output wire quiet,input wire [7:0] tempo
);
 reg [15:0] index;reg [95:0] current;reg [1:0] state;
 wire [95:0] rom_data;
 song_store storage(clk,rst,panic,play&&!playing,index[11:0],rom_data,stored_events,stored_duration,
  upload_valid,upload_ready,upload_command,upload_index,upload_value,upload_aux,
  upload_pending,uploading,received_entries,expected_word,upload_errors);
 reg [16:0] bar_sample;
 `include "tempo_increment.vh"
 reg [15:0] tempo_fraction;
 wire [18:0] tempo_next={3'd0,tempo_fraction}+{1'b0,tempo_increment(tempo)};
 wire [2:0] advance=tempo_next[18:16];
 wire [32:0] position_next={1'b0,sample_position}+advance;
 wire [17:0] bar_next={1'b0,bar_sample}+advance;
 assign event_kind=current[1:0];assign event_part=current[5:2];
 assign event_note=current[12:6];assign event_velocity=current[19:13];assign event_serial=current[63:32];
 assign quiet=!event_valid&&(!playing||(state==1&&current[95:64]>sample_position)||index>=stored_events);
 always @(posedge clk)begin
  if(rst||panic||stop)begin
   playing<=0;event_valid<=0;state<=0;index<=0;sample_position<=0;bar_position<=0;bar_sample<=0;bar_tick<=0;late_events<=0;tempo_fraction<=0;
  end else begin
   bar_tick<=0;
   if(play&&!playing)begin
    playing<=1;sample_position<=0;index<=0;state<=0;event_valid<=0;bar_position<=0;bar_sample<=0;late_events<=0;bar_tick<=1;tempo_fraction<=0;
   end else if(playing)begin
    if(sample_tick)begin
     sample_position<=position_next[31:0];tempo_fraction<=tempo_next[15:0];
     if(bar_next>=96000)begin bar_sample<=bar_next-96000;bar_position<=bar_position+1'b1;bar_tick<=1;end
     else bar_sample<=bar_next[16:0];
    end
    if(sample_tick&&position_next>=stored_duration)begin playing<=0;event_valid<=0;end
    else case(state)
     0:if(index<stored_events)state<=3;
     3:begin current<=rom_data;state<=1;end
     1:if(current[95:64]<=sample_position)begin
      event_valid<=1;state<=2;
      if(sample_position-current[95:64]>1)late_events<=late_events+1'b1;
     end
     2:if(event_ready)begin event_valid<=0;index<=index+1'b1;state<=0;end
    endcase
   end
  end
 end
endmodule
