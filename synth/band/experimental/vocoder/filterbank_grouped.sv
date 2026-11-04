// Same sixteen two-biquad bands and coefficient order as the original filterbank.
// Four lanes keep histories indexed by {filter stage, band group}; only the
// current group travels to the biquads. The three passes are independent per band.
module filterbank #(parameter COEFF_FILE="coeffs.mem",N_FILTERS=16,COEFF_WIDTH=32)(
 input wire clk_in,rst_in,valid_in,
 input wire signed[31:0]carrier_sample_in,modulator_sample_in,
 output reg signed[31:0]carrier_out[N_FILTERS-1:0],envelope_out[N_FILTERS-1:0],
 output wire ready_out,output reg valid_out
);
 localparam IDLE=0,FETCH=1,PREPARE=2,LAUNCH=3,WAIT_RESULT=4;
 localparam MODULATOR=0,ENVELOPE=1,CARRIER=2;
 reg[2:0]state;reg[1:0]phase,band_group;
 reg signed[31:0]carrier[0:2],modulator[0:2];
 wire[3:0]address={phase,band_group};
 wire[3:0]done;
 reg[11:0]initialized;
 assign ready_out=!rst_in&&state==IDLE;
 function[31:0]magnitude(input[31:0]v);
  magnitude=v==32'h80000000 ? 32'h7fffffff : v[31] ? -v : v;
 endfunction
 reg signed[31:0]coefficients[0:169];
 initial begin
  if(N_FILTERS!=16)$fatal(1,"sixteen bands required");
  $readmemh(COEFF_FILE,coefficients);
 end
 always @(posedge clk_in)begin
  valid_out<=0;
  if(rst_in)begin state<=IDLE;initialized<=0;phase<=0;band_group<=0;
   for(integer j=0;j<3;j++)begin carrier[j]<=0;modulator[j]<=0;end
  end else case(state)
   IDLE:if(valid_in)begin
    carrier[0]<=carrier_sample_in;modulator[0]<=modulator_sample_in;
    for(integer j=1;j<3;j++)begin carrier[j]<=carrier[j-1];modulator[j]<=modulator[j-1];end
    phase<=MODULATOR;band_group<=0;state<=FETCH;
   end
   FETCH:state<=PREPARE;
   PREPARE:state<=LAUNCH;
   LAUNCH:state<=WAIT_RESULT;
   WAIT_RESULT:if(&done)begin
    initialized[address]<=1;
    if(phase!=CARRIER)begin phase<=phase+1'b1;state<=FETCH;end
    else if(band_group!=3)begin band_group<=band_group+1'b1;phase<=MODULATOR;state<=FETCH;end
    else begin state<=IDLE;valid_out<=1;end
   end
   default:state<=IDLE;
  endcase
 end
 for(genvar i=0;i<4;i++)begin:lane
  wire[3:0]band={band_group,i[1:0]};
  reg[127:0]history[0:11] /* synthesis syn_ramstyle="distributed_ram" */;reg[127:0]past;
  wire signed[31:0]intermediate,result;
  reg signed[31:0]env_source[0:2],input_taps[0:2];
  reg signed[31:0]coeff[0:9];
  always @(posedge clk_in)begin
   if(state==FETCH)begin
    past<=initialized[address]?history[address]:128'd0;
    for(integer k=0;k<10;k++)begin
     if(phase==ENVELOPE)coeff[k]<=coefficients[160+k];
     else case(band_group)
      0:coeff[k]<=coefficients[10*i+k];
      1:coeff[k]<=coefficients[40+10*i+k];
      2:coeff[k]<=coefficients[80+10*i+k];
      3:coeff[k]<=coefficients[120+10*i+k];
     endcase
    end
   end
   if(state==PREPARE)
    for(integer k=0;k<3;k++)case(phase)
     MODULATOR:input_taps[k]<=modulator[k];
     ENVELOPE:input_taps[k]<=magnitude(env_source[k]);
     CARRIER:input_taps[k]<=carrier[k];
    endcase
   if(!rst_in&&state==WAIT_RESULT&&(&done))begin
    history[address]<={intermediate,past[127:96],result,past[63:32]};
    if(phase==MODULATOR)begin env_source[0]<=result;env_source[1]<=past[63:32];env_source[2]<=past[31:0];end
   end
  end
  // Four fixed output slots per lane, no cross-lane write arbitration.
  for(genvar g=0;g<4;g++)begin:out_band
   always @(posedge clk_in)begin
    if(rst_in)begin envelope_out[g*4+i]<=0;carrier_out[g*4+i]<=0;end
    else if(state==WAIT_RESULT&&(&done)&&band_group==g)begin
     if(phase==ENVELOPE)envelope_out[g*4+i]<=result;
     if(phase==CARRIER)carrier_out[g*4+i]<=result;
    end
   end
  end
  double_biquad #(.COEFF_WIDTH(COEFF_WIDTH)) biquad(
   clk_in,rst_in,state==LAUNCH,coeff[0],coeff[1],coeff[2],coeff[3],coeff[4],
   coeff[5],coeff[6],coeff[7],coeff[8],coeff[9],input_taps[0],input_taps[1],input_taps[2],
   past[127:96],past[95:64],past[63:32],past[31:0],intermediate,result,done[i]);
 end
endmodule

