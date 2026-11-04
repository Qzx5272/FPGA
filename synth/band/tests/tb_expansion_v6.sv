`timescale 1ns/1ps
module tb_expansion_v6;
 reg clk=0;always #10 clk=~clk;
 reg audio=0,run_audio=1;always #20.345052 if(run_audio)audio=~audio;
 reg play=0,stop=0,panic=0;wire bck,ws,sd,clock_fault,mic_stale;wire[11:0]guide;
 wire[31:0]drops,under;wire[3:0]part;wire[111:0]values;
 workstation_expansion_top dut(.clk(clk),.audio_clk(audio),.pc_rx(1'b1),.ble_rx(1'b1),.usb_rx(1'b1),.pc_tx(),.ble_tx(),.usb_tx(),
 .enc_a(8'd0),.enc_b(8'd0),.pedal_raw(4'd0),.adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),
 .mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),.song_next(1'b0),
 .play_button(play),.stop_button(stop),.panic_button(panic),.i2s_bck(bck),.i2s_ws(ws),.i2s_sd(sd),
 .guide_pitch(guide),.guide_bar(),.panel_part(part),.panel_values(values),.clock_fault(clock_fault),.microphone_stale(mic_stale),.drops(drops),.underruns(under));
 // Compress the already unit-tested5ms button debounce in this integration test.
 defparam dut.engine.local_inputs.play_button.STABLE_CYCLES=3;
 defparam dut.engine.local_inputs.stop_button.STABLE_CYCLES=3;
 integer frames=0,nonzero=0;reg saw_guide=0,saw_panic_capture=0;
 always @(posedge clk)begin
 if(guide)saw_guide<=1;
 if(dut.engine.event_capture_valid&&dut.engine.event_capture_data[15:8]==8'he0)saw_panic_capture<=1;
 if(dut.pcm_valid)begin frames<=frames+1;if(dut.left!=0)nonzero<=nonzero+1;end
 end
 initial begin
 wait(!dut.rst);wait(!clock_fault);repeat(500)@(negedge clk);
 if(dut.engine.playing)$fatal(1,"expansion should power up silent");
 play=1;repeat(8)@(negedge clk);play=0;
 wait(frames>140);if(!saw_guide||nonzero==0||drops||under||dut.engine.deadline_miss)$fatal(1,"integrated score/guide/I2S/audio failure frames=%0d guide=%b nonzero=%0d playing=%b pos=%0d voices=%0d deadline=%0d clips=%0d drops=%0d under=%0d",frames,saw_guide,nonzero,dut.engine.playing,dut.engine.song_position,dut.engine.active_voices,dut.engine.deadline_miss,dut.engine.clips,drops,under);
 stop=1;repeat(8)@(negedge clk);stop=0;repeat(100)@(negedge clk);
 if(dut.engine.playing||guide)$fatal(1,"local stop or guide clear");
 run_audio=0;repeat(51000)@(negedge clk);if(!clock_fault||bck||ws||sd)$fatal(1,"stopped audio clock protection");
 run_audio=1;wait(!clock_fault);repeat(100)@(negedge clk);
 if(dut.engine.playing)$fatal(1,"clock recovery must not restart song");
 if(!saw_panic_capture)$fatal(1,"panic not captured for event recording");
 $display("PASS expansion: real integrated score,local play/stop,guide,standard I2S CDC,zero drop/underrun/deadline,audio-clock loss and silent recovery");$finish;
 end
 initial begin #20000000;$fatal(1,"timeout frames=%0d",frames);end
endmodule
