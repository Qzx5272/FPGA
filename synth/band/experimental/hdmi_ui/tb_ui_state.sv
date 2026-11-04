module tb_ui_state;
 reg clk=0,pixel=0;always #10 clk=~clk;always #19 pixel=~pixel;
 reg rst=1,prst=1,frame=0,accepted=0,panic=0;reg[223:0]packet=0;
 wire[127:0]snapshot;wire[127:0]display_data;
 ui_state observer(clk,rst,panic,accepted,packet,1'b0,7'd64,8'd120,16'd3,snapshot);
 ui_snapshot bridge(clk,pixel,rst,prst,frame,snapshot,display_data);
 task send_event(input[7:0]kind,input[7:0]source,input[6:0]note,input[6:0]velocity);
 begin @(negedge clk);packet=0;packet[15:8]=kind;packet[23:16]=source;packet[27:24]=8;packet[46:40]=note;packet[54:48]=velocity;accepted=1;@(negedge clk);accepted=0;end endtask
 reg[127:0]before_frame;
 initial begin
  repeat(4)@(negedge clk);rst=0;prst=0;
  send_event(0,3,65,90);if(snapshot[98:67]!=0)$fatal(1,"phone confused with pad");
  send_event(0,2,70,98);
  if(snapshot[38:32]!=70||snapshot[45:39]!=98||snapshot[49:46]!=8||snapshot[60]!=1||snapshot[66]!=1||snapshot[98:67]!=1)$fatal(1,"strike fields");
  repeat(10)@(negedge pixel);if(display_data!=0)$fatal(1,"not frame atomic");
  frame=1;@(negedge pixel);frame=0;
  // First frame may commit the boot snapshot; next handshake brings the hit.
  repeat(10)@(negedge pixel);frame=1;@(negedge pixel);frame=0;
  if(display_data!=snapshot)$fatal(1,"snapshot mismatch");before_frame=display_data;
  send_event(0,2,75,110);repeat(10)@(negedge pixel);if(display_data!=before_frame)$fatal(1,"torn frame");
  frame=1;@(negedge pixel);frame=0;repeat(10)@(negedge pixel);frame=1;@(negedge pixel);frame=0;
  if(display_data[38:32]!=75)$fatal(1,"updated snapshot missing");
  @(negedge clk);panic=1;@(negedge clk);panic=0;if(snapshot[65:50]!=0)$fatal(1,"panic highlight");
  // Accelerate only the slow countdown for expiry coverage.
  repeat(101)begin @(negedge clk);observer.divider=499999;@(negedge clk);end
  if(snapshot[66]!=0)$fatal(1,"stale bridge still online");
  $display("PASS source distinction, fields, highlights, stale bridge, frame-atomic CDC");$finish;
 end
endmodule

