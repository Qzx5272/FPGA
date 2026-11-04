`include "song_config.vh"
// Autonomous event ROM score. No dependency on host timing after play.
module song_sequencer(
 input wire clk,rst,panic,sample_tick,play,stop,
 output reg playing,bar_tick,
 output reg event_valid,input wire event_ready,
 output wire [1:0] event_kind,output wire [3:0] event_part,
 output wire [6:0] event_note,event_velocity,output wire [31:0] event_serial,
 output reg [31:0] sample_position,late_events,
 output reg [7:0] bar_position
);
 reg [95:0] song_rom[0:`SONG_EVENTS-1];
 initial begin
  `include "song_events.vh"
 end
 reg [15:0] index;reg [95:0] current;reg [1:0] state;
 reg [16:0] bar_sample;
 assign event_kind=current[1:0];assign event_part=current[5:2];
 assign event_note=current[12:6];assign event_velocity=current[19:13];assign event_serial=current[63:32];
 always @(posedge clk)begin
  if(rst||panic||stop)begin
   playing<=0;event_valid<=0;state<=0;index<=0;sample_position<=0;bar_position<=0;bar_sample<=0;bar_tick<=0;late_events<=0;
  end else begin
   bar_tick<=0;
   if(play&&!playing)begin
    playing<=1;sample_position<=0;index<=0;state<=0;event_valid<=0;bar_position<=0;bar_sample<=0;late_events<=0;bar_tick<=1;
   end else if(playing)begin
    if(sample_tick)begin
     sample_position<=sample_position+1'b1;
     if(bar_sample==95999)begin bar_sample<=0;bar_position<=bar_position+1'b1;bar_tick<=1;end
     else bar_sample<=bar_sample+1'b1;
     if(sample_position==`SONG_LENGTH-1)begin playing<=0;event_valid<=0;end
    end
    case(state)
     0:if(index<`SONG_EVENTS)begin current<=song_rom[index];state<=1;end
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
