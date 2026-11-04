`timescale 1ns/1ps
module tb;
 GSR GSR(.GSRI(1'b1));
reg clk=0;always #10 clk=~clk;
reg rst=1,panic=0,sample_valid=0,config_valid=0,event_ready=0,config_invert=0;
reg[2:0]sample_channel=0;reg[119:0]samples=0;
reg[6:0]config_channel=0,on_threshold=20,off_threshold=8;
reg[11:0]config_baseline=0;reg[15:0]config_gain=127;
wire event_valid,event_off,exhausted;wire[6:0]event_contact,event_pressure;
wire[31:0]event_serial,overruns;wire[559:0]pressure_values;
wire rv,ro,re;wire[6:0]rc,rp;wire[31:0]rs,rov;wire[559:0]rvalues;
stage_pad_frontend dut(.*);
stage_pad_reference refdut(.clk(clk),.rst(rst),.panic(panic),.sample_valid(sample_valid),.sample_channel(sample_channel),.samples(samples),.config_valid(config_valid),.config_channel(config_channel),.config_baseline(config_baseline),.config_gain(config_gain),.config_invert(config_invert),.on_threshold(on_threshold),.off_threshold(off_threshold),.event_ready(event_ready),.event_valid(rv),.event_off(ro),.event_contact(rc),.event_pressure(rp),.event_serial(rs),.pressure_values(rvalues),.overruns(rov),.exhausted(re));
integer n,j,events=0,presses=0,offs=0;reg[31:0]random_state=32'h83742615;
initial begin
 repeat(3)@(negedge clk);rst=0;
 for(n=0;n<200000;n=n+1)begin
  @(negedge clk);
  if({event_valid,pressure_values,overruns,exhausted}!=={rv,rvalues,rov,re})$fatal(1,"state mismatch cycle%0d",n);
  if(event_valid&&{event_off,event_contact,event_pressure,event_serial}!=={ro,rc,rp,rs})$fatal(1,"event mismatch cycle%0d",n);
  if(event_valid&&event_ready)begin events=events+1;if(event_off)offs=offs+1;else presses=presses+1;end
  random_state={random_state[30:0],random_state[31]^random_state[21]^random_state[1]^random_state[0]};
  sample_valid=n%53==0;sample_channel=(n/53)%8;
  for(j=0;j<10;j=j+1)samples[j*12+:12]=random_state[(j%4)*8+:8]>100?12'd3600:12'd0;
  event_ready=n%1000>700&&random_state[3];
  panic=n%17003==17002;rst=n%70001==70000;
  config_valid=n%391==0;config_channel=(n/391)%80;config_gain=127;config_baseline=random_state[11:0]&12'h0ff;config_invert=random_state[17];
 end
 if(presses<100||offs<100)$fatal(1,"insufficient events");
 $display("PASS200000 cycle exact differential events=%0d presses=%0d releases=%0d",events,presses,offs);$finish;
end
endmodule
