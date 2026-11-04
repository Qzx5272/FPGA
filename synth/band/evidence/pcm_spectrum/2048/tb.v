`timescale 1ns/1ps
module tb;
localparam N=2048,LOG_N=11;
reg ac=0,dc=0,run=0;always #7 ac=~ac;always #5 if(run)dc=~dc;
reg rst=1,pv=0,ready=0;reg signed[15:0]l=0,r=0;
wire valid;wire[LOG_N-1:0]bin;wire signed[15:0]yr,yi;
wire[31:0]frame,last,skipped,clips;wire[16:0]pl,pr;
reg[15:0]data[0:N-1];integer i,j,file,audio_count=0,before_count;
reg signed[15:0]held_r,held_i;
pcm_spectrum #(.LOG_N(LOG_N),.TWIDDLE_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/audio_visual/fft_twiddle_2048.mem"),.WINDOW_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/audio_visual/hann_2048.mem")) dut(
ac,dc,rst,pv,l,r,valid,ready,bin,yr,yi,frame,last,pl,pr,skipped,clips);
always @(posedge ac)if(!rst&&pv)audio_count=audio_count+1;
initial begin
 $readmemh("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/evidence/pcm_spectrum/2048/input.hex",data);file=$fopen("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/evidence/pcm_spectrum/2048/bins.txt","w");
 run=1;repeat(3)@(negedge dc);rst=0;run=0;
 // Samples presented during the documented reset-release window are not accepted.
 wait(!dut.capture.write_reset);
 for(i=0;i<N;i=i+1)begin @(negedge ac);pv=1;l=data[i];r=-1234;end
 @(negedge ac);l=0;r=0;
 repeat(64)@(negedge ac);if(skipped<64)$fatal(1,"stopped analysis clock did not count skipped visual samples");
 run=1;wait(valid);@(negedge dc);
 if(frame!=1||last!=N-1||pl!=18982||pr!=1234)$fatal(1,"metadata not bound to first window");
 before_count=audio_count;
 for(j=0;j<N;j=j+1)begin
  while(!valid)@(negedge dc);
  if(bin!=j)$fatal(1,"bin order");held_r=yr;held_i=yi;
  if(j%17==0)repeat(20)begin
   @(negedge dc);if(!valid||bin!=j||yr!==held_r||yi!==held_i||frame!=1||last!=N-1)$fatal(1,"stalled spectrum changed");
  end
  $fwrite(file,"%0d %0d %0d\n",j,$signed(yr),$signed(yi));ready=1;@(negedge dc);ready=0;
 end
 if(audio_count<=before_count||clips||dut.rejected)$fatal(1,"continuity/clips/start");
 // Shared reset invalidates snapshots, partial transforms, and stale metadata.
 wait(valid);@(negedge dc);run=0;pv=0;rst=1;repeat(3)@(negedge ac);rst=0;
 if(valid)$fatal(1,"reset while clock stopped exposed stale FFT result");
 repeat(3)@(negedge ac);run=1;repeat(6)@(negedge dc);
 if(valid||frame||last||pl||pr||skipped)$fatal(1,"reset stale data");
 $fclose(file);$display("PASS PCM/Hann/FFT N=%0d asynchronous clocks,stopped analysis,output stalls,metadata,reset,audio continued",N);$finish;
end
initial begin #100000000;$fatal(1,"timeout");end
endmodule
