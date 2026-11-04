// Preserve every variable-latency PCM frame before the fixed-rate PT8211 DAC.
// Same verified serializer and pins as the released board; no new pin mapping.
module audio_pt8211_queue #(parameter START_FRAMES=2)(
 input wire clk,rst,panic,frame_valid,
 input wire signed [15:0] left_in,right_in,
 output wire frame_ready,sample_tick,bck,ws,din,
 output reg [31:0] dropped_frames,underruns,
 output wire [2:0] queued_frames
);
 reg [31:0] memory[0:3];reg [1:0] read_pointer,write_pointer;reg [2:0] count;
 reg latched_valid,started;
 // Prefill covers completion jitter when a light frame is followed by a
 // full-load frame whose singer processing extends past the next DAC tick.
 wire present=count!=0&&(started||count>=START_FRAMES);
 wire signed [15:0] left=present?memory[read_pointer][31:16]:16'sd0;
 wire signed [15:0] right=present?memory[read_pointer][15:0]:16'sd0;
 // sample_tick is registered by the serializer. Use validity from the edge
 // where it latched PCM, not count after a simultaneous enqueue on that edge.
 wire consume=sample_tick&&latched_valid;
 assign frame_ready=!rst&&!panic&&(count<4||consume);
 assign queued_frames=count;
 wire enqueue=frame_valid&&frame_ready;
 audio_serial #(.MODE_I2S(0)) serializer(clk,rst||panic,left,right,bck,ws,din,sample_tick);
 always @(posedge clk)begin
  if(rst||panic)begin
   read_pointer<=0;write_pointer<=0;count<=0;latched_valid<=0;started<=0;dropped_frames<=0;underruns<=0;
  end else begin
   latched_valid<=present;
   if(enqueue)begin memory[write_pointer]<={left_in,right_in};write_pointer<=write_pointer+1'b1;end
   if(consume)begin read_pointer<=read_pointer+1'b1;started<=1;end
   case({enqueue,consume})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
   if(frame_valid&&!frame_ready&&dropped_frames!=32'hffffffff)dropped_frames<=dropped_frames+1'b1;
   // Startup silence is expected until the first generated frame is consumed.
   if(sample_tick&&!latched_valid&&started&&underruns!=32'hffffffff)underruns<=underruns+1'b1;
  end
 end
endmodule
