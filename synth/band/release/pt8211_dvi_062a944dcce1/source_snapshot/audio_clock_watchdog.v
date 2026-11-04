// Independent audio-clock heartbeat: recovery cannot depend on a serializer
// that is held reset by this fault. Require three observed toggles to re-arm.
// This detects missing edges, not clock-frequency accuracy or PLL lock quality.
module audio_clock_watchdog #(parameter DIV_BITS=7,parameter TIMEOUT_CYCLES=50000)(
 input core_clk,audio_clk,rst,output reg fault,output reg[31:0]losses
);
 // FPGA configuration initializes the heartbeat even when audio_clk is absent
 // from power-up and no sampled reset edge can occur in that domain.
 reg[DIV_BITS-1:0]divider=0;reg heartbeat=0;
 always @(posedge audio_clk or posedge rst)begin
  if(rst)begin divider<=0;heartbeat<=0;end
  else begin divider<=divider+1'b1;if(&divider)heartbeat<=!heartbeat;end
 end
 (* ASYNC_REG="TRUE" *)reg sync1,sync2;reg seen;reg[1:0]recovery;
 localparam TIMER_BITS=$clog2(TIMEOUT_CYCLES+1);
 reg[TIMER_BITS-1:0]idle;
 always @(posedge core_clk)begin
  if(rst)begin sync1<=0;sync2<=0;seen<=0;recovery<=0;idle<=0;fault<=1;losses<=0;end
  else begin
   sync1<=heartbeat;sync2<=sync1;seen<=sync2;
   if(sync2!=seen)begin
    idle<=0;
    if(fault)begin
     if(recovery==2)begin fault<=0;recovery<=0;end else recovery<=recovery+1'b1;
    end
   end else if(idle==TIMEOUT_CYCLES-1)begin
    recovery<=0;
    if(!fault)begin fault<=1;if(losses!=32'hffffffff)losses<=losses+1'b1;end
   end else idle<=idle+1'b1;
  end
 end
endmodule
