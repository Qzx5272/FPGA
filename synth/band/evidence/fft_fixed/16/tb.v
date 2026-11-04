`timescale 1ns/1ps
module tb;
localparam N=16,LOG_N=4;
reg clk=0;always #5 clk=~clk;
reg rst=1,start=0,iv=0,orr=0;wire sr,ir,ov,done;
reg signed[15:0]xr=0,xi=0;wire signed[15:0]yr,yi;wire[LOG_N-1:0]bin;
wire[31:0]rejects,clips;reg[31:0]data[0:6*N-1];integer f,i,j,file,cycles=0,begin_compute=0,max_compute=0;reg signed[15:0]held_r,held_i;
fft_fixed #(.LOG_N(LOG_N),.TWIDDLE_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/audio_visual/fft_twiddle_16.mem")) dut(clk,rst,start,sr,iv,ir,xr,xi,ov,orr,bin,yr,yi,done,rejects,clips);
always @(posedge clk)cycles=cycles+1;
initial begin
 $readmemh("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/evidence/fft_fixed/16/input.hex",data);file=$fopen("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/evidence/fft_fixed/16/bins.txt","w");repeat(3)@(negedge clk);rst=0;#1;
 for(f=0;f<6;f=f+1)begin
  if(!sr)$fatal(1,"not ready for transform");start=1;@(negedge clk);start=0;
  for(i=0;i<N;i=i+1)begin
   if(!ir)$fatal(1,"lost input readiness");{xr,xi}=data[f*N+i];iv=1;start=i==3;@(negedge clk);iv=0;start=0;
   if(i%7==0&&i!=N-1)begin repeat(2)@(negedge clk);if(ov)$fatal(1,"partial input produced result");end
  end
  begin_compute=cycles;wait(ov);@(negedge clk);if(cycles-begin_compute>max_compute)max_compute=cycles-begin_compute;
  for(i=0;i<N;i=i+1)begin
   while(!ov)@(negedge clk);if(bin!=i)$fatal(1,"bin order");held_r=yr;held_i=yi;
   if(i%17==0)repeat(3)begin @(negedge clk);if(!ov||bin!=i||yr!==held_r||yi!==held_i)$fatal(1,"backpressure changed output");end
   $fwrite(file,"%0d %0d %0d %0d\n",f,i,$signed(yr),$signed(yi));orr=1;@(negedge clk);orr=0;
  end
  if(!done||!sr||(f<5?clips!=0:clips==0)||rejects!=f+1)$fatal(1,"completion/counters clips=%0d rejects=%0d",clips,rejects);
 end
 start=1;@(negedge clk);start=0;iv=1;repeat(3)@(negedge clk);iv=0;rst=1;repeat(2)@(negedge clk);rst=0;
 repeat(4)@(negedge clk);if(ov||!sr||rejects||clips)$fatal(1,"reset did not discard partial load");
 $fclose(file);$display("PASS FFT N=%0d transforms=6 max_compute_clocks=%0d,stall/input gaps/busy start/reset",N,max_compute);$finish;
end
initial begin #1000000000;$fatal(1,"timeout");end
endmodule
