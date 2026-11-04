// Nonblocking left-channel PCM spectrum. Frozen stereo snapshot -> periodic Hann
// -> normalized complex FFT. Bins are X_windowed[k]/N, not calibrated dB SPL.
// Audio and analysis clocks may stop independently; common reset required.
module pcm_spectrum #(
 parameter LOG_N=11,parameter TWIDDLE_FILE="fft_twiddle_2048.mem",
 parameter WINDOW_FILE="hann_2048.mem"
)(
 input audio_clk,analysis_clk,rst,pcm_valid,
 input signed[15:0]pcm_left,pcm_right,
 output spectrum_valid,input spectrum_ready,output[LOG_N-1:0]spectrum_bin,
 output signed[15:0]spectrum_real,spectrum_imag,
 output reg[31:0]spectrum_frame,spectrum_last_sample,
 output reg[16:0]peak_left,peak_right,
 output[31:0]visualization_skipped,fft_clips
);
 localparam IDLE=0,REQUEST=1,WAIT_READ=2,MULTIPLY=3,SEND=4,WAIT_FFT=5;
 reg[2:0]state;reg[LOG_N-1:0]index;
 reg[15:0]window[0:(1<<LOG_N)-1];reg[15:0]coefficient;
 reg signed[15:0]sample;reg signed[32:0]product;
 initial $readmemh(WINDOW_FILE,window);
 // Remember reset while the analysis clock is absent; the synchronous FFT
 // must see reset on restart before any pre-panic state can become visible.
 (* ASYNC_REG="TRUE" *) reg[1:0]reset_sync;
 always @(posedge analysis_clk or posedge rst)
  if(rst)reset_sync<=2'b11;else reset_sync<={reset_sync[0],1'b0};
 wire analysis_rst=rst||reset_sync[1];wire fft_valid;
 assign spectrum_valid=fft_valid&&!analysis_rst;
 wire available,read_valid,start_ready,input_ready,done;
 wire signed[15:0]read_left,read_right;
 wire[16:0]captured_left,captured_right;
 wire[31:0]last_sample,frame_number,rejected;
 wire start=!analysis_rst&&state==IDLE&&available&&start_ready;
 wire release_frame=state==SEND&&input_ready&&index==((1<<LOG_N)-1);
 pcm_snapshot #(.ADDRESS_BITS(LOG_N)) capture(
  .audio_clk(audio_clk),.read_clk(analysis_clk),.rst(rst),.pcm_valid(pcm_valid),
  .pcm_left(pcm_left),.pcm_right(pcm_right),.read_enable(state==REQUEST),
  .read_address(index),.release_frame(release_frame),.frame_available(available),
  .read_valid(read_valid),.read_left(read_left),.read_right(read_right),
  .frame_peak_left(captured_left),.frame_peak_right(captured_right),
  .frame_last_sample(last_sample),.frame_number(frame_number),.visualization_skipped(visualization_skipped));
 wire signed[15:0]windowed=product>>>15;
 fft_fixed #(.LOG_N(LOG_N),.TWIDDLE_FILE(TWIDDLE_FILE)) transform(
  .clk(analysis_clk),.rst(analysis_rst),.start(start),.start_ready(start_ready),
  .input_valid(state==SEND),.input_ready(input_ready),.input_real(windowed),.input_imag(16'sd0),
  .output_valid(fft_valid),.output_ready(spectrum_ready),.output_bin(spectrum_bin),
  .output_real(spectrum_real),.output_imag(spectrum_imag),.done(done),
  .rejected_starts(rejected),.clip_count(fft_clips));
 always @(posedge analysis_clk)begin
  if(analysis_rst)begin
   state<=IDLE;index<=0;coefficient<=0;sample<=0;product<=0;
   spectrum_frame<=0;spectrum_last_sample<=0;peak_left<=0;peak_right<=0;
  end else case(state)
   IDLE:if(start)begin
    index<=0;state<=REQUEST;spectrum_frame<=frame_number;
    spectrum_last_sample<=last_sample;peak_left<=captured_left;peak_right<=captured_right;
   end
   REQUEST:begin coefficient<=window[index];state<=WAIT_READ;end
   WAIT_READ:if(read_valid)begin sample<=read_left;state<=MULTIPLY;end
   MULTIPLY:begin product<=sample*$signed({1'b0,coefficient});state<=SEND;end
   SEND:if(input_ready)begin
    if(index==((1<<LOG_N)-1))state<=WAIT_FFT;
    else begin index<=index+1'b1;state<=REQUEST;end
   end
   WAIT_FFT:if(done)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
