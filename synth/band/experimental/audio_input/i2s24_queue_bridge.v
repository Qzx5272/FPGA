// Core PCM -> asynchronous FIFO -> two-frame prefill -> standard I2S.
// audio_clk=24.576MHz. Use sample_tick to pace synthesis; no ASRC or PLL here.
// Exclude intentional prefill silence from underruns; count gaps after startup.
module i2s24_queue_bridge(
 input core_clk,audio_clk,rst,panic,frame_valid,
 input signed[23:0]left_in,right_in,
 output frame_ready,sample_tick,bck,ws,sd,
 output reg[31:0]dropped_frames,output reg[31:0]underruns_audio_domain,
 output reg[31:0]underruns_core_domain
);
 wire reset_async=rst||panic;
 (* ASYNC_REG="TRUE" *)reg[1:0]core_reset,audio_reset;
 always @(posedge core_clk or posedge reset_async)
  if(reset_async)core_reset<=3;else core_reset<={core_reset[0],1'b0};
 always @(posedge audio_clk or posedge reset_async)
  if(reset_async)audio_reset<=3;else audio_reset<={audio_reset[0],1'b0};
 wire fifo_ready,fifo_valid;wire[47:0]fifo_data;
 wire fetch;assign frame_ready=!reset_async&&!core_reset[1]&&fifo_ready;
 audio_cdc_fifo fifo(core_clk,core_reset[1],frame_valid,{left_in,right_in},fifo_ready,
  audio_clk,audio_reset[1],fetch,fifo_valid,fifo_data);
 reg[47:0]queue[0:3];reg[1:0]read_pointer,write_pointer;reg[2:0]count;
 reg started,latched_present,previous_request,under_toggle;
 wire present=count!=0&&(started||count>=2);
 wire pop,request;wire[47:0]data=present?queue[read_pointer]:48'd0;
 wire consume=pop;
 assign fetch=!audio_reset[1]&&fifo_valid&&(count<4||consume);
 wire raw_bck,raw_ws,raw_sd;wire[31:0]raw_underruns;
 i2s24_tx serializer(audio_clk,audio_reset[1],data,present,pop,request,raw_bck,raw_ws,raw_sd,raw_underruns);
 assign bck=reset_async||audio_reset[1]?1'b0:raw_bck;
 assign ws=reset_async||audio_reset[1]?1'b0:raw_ws;
 assign sd=reset_async||audio_reset[1]?1'b0:raw_sd;
 always @(posedge audio_clk)begin
  if(audio_reset[1])begin
   read_pointer<=0;write_pointer<=0;count<=0;started<=0;latched_present<=0;previous_request<=0;underruns_audio_domain<=0;under_toggle<=0;
  end else begin
   previous_request<=request;latched_present<=present;
   if(fetch)begin queue[write_pointer]<=fifo_data;write_pointer<=write_pointer+1'b1;end
   if(consume)begin read_pointer<=read_pointer+1'b1;started<=1;end
   case({fetch,consume})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
   if(request!=previous_request&&!latched_present&&started&&underruns_audio_domain!=32'hffffffff)begin
    underruns_audio_domain<=underruns_audio_domain+1'b1;under_toggle<=!under_toggle;end
  end
 end
 (* ASYNC_REG="TRUE" *)reg request1,request2;reg seen;
 // At most one underrun per48kHz frame; core clock must keep running fast
 // enough to observe toggles. Never sample an asynchronous binary counter.
 (* ASYNC_REG="TRUE" *)reg under1,under2;reg under_seen;
 assign sample_tick=!core_reset[1]&&(request2!=seen);
 always @(posedge core_clk or posedge reset_async)begin
  if(reset_async)begin request1<=0;request2<=0;seen<=0;dropped_frames<=0;under1<=0;under2<=0;under_seen<=0;underruns_core_domain<=0;end
  else if(core_reset[1])begin request1<=0;request2<=0;seen<=0;dropped_frames<=0;under1<=0;under2<=0;under_seen<=0;underruns_core_domain<=0;end
  else begin
   request1<=request;request2<=request1;seen<=request2;
   under1<=under_toggle;under2<=under1;under_seen<=under2;
   if(under2!=under_seen&&underruns_core_domain!=32'hffffffff)underruns_core_domain<=underruns_core_domain+1'b1;
   if(frame_valid&&!frame_ready&&dropped_frames!=32'hffffffff)dropped_frames<=dropped_frames+1'b1;
  end
 end
endmodule
