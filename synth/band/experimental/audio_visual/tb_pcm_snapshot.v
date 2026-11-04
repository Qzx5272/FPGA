`timescale 1ns/1ps
module tb_pcm_snapshot #(parameter AB=9);
 localparam N=1<<AB;
 reg ac=0,rc=0,rst=1,v=0,en=0,release_frame=0;always #10 ac=~ac;always #7 rc=~rc;
 reg signed[15:0] l=0,r=0;reg[AB-1:0]addr=0;
 wire available,valid;wire signed[15:0]ol,orr;wire[16:0]pl,pr;wire[31:0]last,num,skipped;
 pcm_snapshot #(.ADDRESS_BITS(AB))dut(ac,rc,rst,v,l,r,en,addr,release_frame,available,valid,ol,orr,pl,pr,last,num,skipped);
 integer i;reg[31:0]saved_skipped;
 task sample(input signed[15:0]left,input signed[15:0]right);begin
  @(negedge ac);v=1;l=left;r=right;@(negedge ac);v=0;
 end endtask
 task read_sample(input[AB-1:0]index,input signed[15:0]left,input signed[15:0]right);begin
  @(negedge rc);addr=index;en=1;@(negedge rc);
  if(!valid||ol!==left||orr!==right)$fatal(1,"RAM read mismatch index=%0d L=%0d R=%0d",index,ol,orr);
  en=0;
 end endtask
 initial begin
  #40;rst=0;repeat(3)@(negedge rc);
  en=1;repeat(2)@(negedge rc);if(valid||available)$fatal(1,"uninitialized frame exposed");en=0;
  for(i=0;i<N;i=i+1)sample(i==N-1?-32768:i,-i);
  wait(available);#1;
  if(num!=1||last!=N-1||pl!=32768||pr!=N-1)$fatal(1,"first metadata");
  // Consumer has not released: unrelated new PCM must not overwrite snapshot.
  for(i=0;i<37;i=i+1)sample(1000+i,2000+i);
  if(skipped!=37)$fatal(1,"reader stall drop accounting");
  for(i=0;i<N;i=i+1)read_sample(i,i==N-1?-32768:i,-i);
  if(num!=1||last!=N-1)$fatal(1,"metadata changed while reader owns window");
  @(negedge rc);release_frame=1;en=1;@(negedge rc);if(valid||available)$fatal(1,"release did not invalidate read");release_frame=0;en=0;
  repeat(8)@(negedge ac);
  for(i=0;i<N;i=i+1)sample(300+i,-300-i);
  wait(available);#1;if(num!=2||last!=2*N+36||pl!=N+299||pr!=N+299)$fatal(1,"second metadata");
  for(i=N-1;i>=0;i=i-1)read_sample(i,300+i,-300-i);
  // Reset with a published frame must revoke it and require a whole new window.
  rst=1;#40;rst=0;repeat(5)@(negedge rc);if(available||valid||skipped)$fatal(1,"reset stale frame");
  for(i=0;i<N-1;i=i+1)sample(i,i);
  repeat(5)@(negedge rc);if(available)$fatal(1,"partial frame exposed");
  sample(N-1,N-1);wait(available);#1;if(num!=1||last!=N-1)$fatal(1,"post-reset window");
  $display("PASS real PCM snapshot: asynchronous clocks,all stereo samples,negative full scale,stable metadata,37 skipped visualization samples,release/reset/partial-window gates");$finish;
 end
 initial begin #500000;$fatal(1,"timeout");end
endmodule
