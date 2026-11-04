`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg rst=1,panic=0,event_valid=0,retire_valid=0,probe_only=0;
reg[1:0]kind=0;reg[7:0]source=2,contact=0;
reg[3:0]part=6;reg[31:0]epoch=1,serial=0,retire_generation=0;
reg[6:0]note=60,velocity=100;reg[4:0]retire_slot=0,query_slot=0;
wire ready,lead,done;
shared_note_allocator dut(.clk(clk),.rst(rst),.panic(panic),.event_valid(event_valid),.event_ready(ready),
 .event_kind(kind),.event_source(source),.event_contact(contact),.event_part(part),.event_epoch(epoch),.event_serial(serial),
 .event_note(note),.event_velocity(velocity),.retire_valid(retire_valid),.retire_slot(retire_slot),.retire_generation(retire_generation),
 .query_slot(query_slot),.probe_only(probe_only),.lead_active(lead),.done(done));
integer i,n,checks=0,lead_cycles=0,empty_cycles=0,retired=0,committed=0;reg expected;reg[31:0]rng=32'h143921ab;
always @(negedge clk)if(!rst)begin
 expected=0;
 for(i=0;i<32;i=i+1)begin
  if(dut.lead_slots[i] !== (dut.active[i]&&(dut.part[i]==6)))$fatal(1,"lead identity cache mismatch slot%0d",i);
  expected=expected|(dut.active[i]&&(dut.part[i]==6));
 end
 if(lead!==expected)$fatal(1,"aggregate lead mismatch");
 checks=checks+1;if(lead)lead_cycles=lead_cycles+1;else empty_cycles=empty_cycles+1;
end
always @(posedge clk)if(!rst&&!panic)begin
 if(retire_valid&&dut.active[retire_slot]&&!dut.gate[retire_slot]&&dut.generation[retire_slot]==retire_generation)retired=retired+1;
 if(dut.state==2&&!dut.probing&&dut.kind==0&&!dut.found_match&&dut.found_free&&!dut.exhausted&&dut.vel!=0)committed=committed+1;
end
initial begin
 repeat(4)@(posedge clk);#1;rst=0;
 for(n=0;n<200000;n=n+1)begin
  @(posedge clk);#1;
  rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
  panic=(n%40001==40000);rst=(n==100003);
  event_valid=ready;kind=(rng[3:0]<10)?0:(rng[5]?2:1);
  part=rng[6]?6:rng[10:7];serial=n/128;contact=rng[18:11];source=2;
  probe_only=rng[23:20]==0;velocity=rng[29:24]==0?0:100;
  retire_slot=rng[4:0];retire_valid=rng[9];
  retire_generation=dut.generation[retire_slot]+(rng[10]?0:1);
 end
 @(negedge clk);
 if(checks<190000||lead_cycles==0||empty_cycles==0||retired==0||committed<100)$fatal(1,"insufficient exercised transitions");
 $display("PASS cached lead bitmap cycles=%0d lead=%0d empty=%0d allocations=%0d retired=%0d",checks,lead_cycles,empty_cycles,committed,retired);$finish;
end
endmodule
