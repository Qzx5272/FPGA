// J20 RGB666 panel; 800x480 DE timing proven by the local color-bar probe.
module board_lcd_ui_top(input clk,uart_rx_pin,ble_rx,key_play_n,key_stop_n,key_panic_n,
 output uart_tx_pin,ble_tx,HP_BCK,HP_WS,HP_DIN,PA_EN,
 output lcd_clk,lcd_en,lcd_hs,lcd_vs,lcd_bl,output[5:0]lcd_r,lcd_g,lcd_b);
 wire rst,panic,audio_stop;wire[127:0]core_state,display_state;
 band_stage_pt8211_engine #(.EXTERNAL_AUDIO(0),.LOCAL_INPUTS(1),.LOCAL_ANALOG(0)) engine(
 .clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),.ble_rx(ble_rx),.ble_tx(ble_tx),
 .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),.ui_snapshot_data(core_state),
 .adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),
 .local_play(~key_play_n),.local_stop(~key_stop_n),.local_panic(~key_panic_n),
 .local_root(4'd0),.local_minor(1'b0),.local_held(),.external_sample_tick(1'b0),
 .pcm_left(),.pcm_right(),.pcm_valid(),.reset_out(rst),.panic_out(panic),
 .microphone_sample(24'sd0),.singer_mix(7'd0),.dac_dropped(),.dac_underruns(),
 .singer_gate(),.singer_note(),.transport_sample_tick(),.audio_stop(audio_stop),
 .pedal_raw(4'd0),.pedal_down(),.deferred_returns());
 wire pixel,locked;Gowin_PLL clockgen(pixel,clk,locked);
 wire async_reset=rst||!locked;
 (* ASYNC_REG="TRUE" *)reg[2:0]release_hold=0;
 always @(posedge pixel or posedge async_reset)if(async_reset)release_hold<=0;else release_hold<={release_hold[1:0],1'b1};
 wire pixel_rst=!release_hold[2];reg[10:0]h=0;reg[9:0]v=0;
 always @(posedge pixel)begin
  if(pixel_rst)begin h<=0;v<=0;end
  else if(h==1191)begin h<=0;if(v==532)v<=0;else v<=v+1'b1;end else h<=h+1'b1;
 end
 wire active=h>=182&&h<982&&v>=8&&v<488;
 wire in_view=h>=262&&h<902&&v>=8&&v<488;
 wire[9:0]x=in_view?h-11'd262:10'd0,y=active?v-10'd8:10'd0;
 wire frame_start=h==0&&v==0;wire[23:0]ui_rgb;wire ui_de,ui_hs,ui_vs;
 ui_snapshot ui_cdc(clk,pixel,rst,pixel_rst,frame_start,core_state,display_state);
 instrument_ui dashboard(pixel,pixel_rst,x,y,active,1'b1,1'b1,display_state,ui_rgb,ui_de,ui_hs,ui_vs);
 reg[2:0]inside_pipe=0;
 always @(posedge pixel)if(pixel_rst)inside_pipe<=0;else inside_pipe<={inside_pipe[1:0],in_view};
 wire[23:0]color=inside_pipe[2]?ui_rgb:24'h0b1424;
 assign {lcd_r,lcd_g,lcd_b}=ui_de?{color[23:18],color[15:10],color[7:2]}:18'd0;
 assign lcd_clk=~pixel;assign lcd_en=ui_de;
 assign lcd_hs=1'b1;assign lcd_vs=1'b1;assign lcd_bl=release_hold[2];
endmodule
