`define GOWIN_PRIMITIVES
// Explicit 16-bit RAM prevents Gowin merging a 16-bit tail into a half-empty
// 32-bit SDPB, which consumed two physical blocks for one useful 16-bit array.
module partial_ram16 #(parameter ADDRESS_BITS=9)(
 input wire clk,we,re,input wire [ADDRESS_BITS-1:0] wa,ra,
 input wire [15:0] data,output wire [15:0] q
);
`ifdef GOWIN_PRIMITIVES
 wire [31:0] output_word;
 SDPB #(.BIT_WIDTH_0(16),.BIT_WIDTH_1(16),.READ_MODE(1'b0),.RESET_MODE("SYNC")) ram(
  .CLKA(clk),.CLKB(clk),.CEA(we),.CEB(re),.OCE(1'b0),.RESET(1'b0),
  .BLKSELA(3'd0),.BLKSELB(3'd0),
  .ADA({{(10-ADDRESS_BITS){1'b0}},wa,4'b0011}),.ADB({{(10-ADDRESS_BITS){1'b0}},ra,4'd0}),
  .DI({16'd0,data}),.DO(output_word));
 assign q=output_word[15:0];
`else
 reg [15:0] memory[0:(1<<ADDRESS_BITS)-1];reg [15:0] output_word;
 always @(posedge clk)begin if(we)memory[wa]<=data;if(re)output_word<=memory[ra];end
 assign q=output_word;
`endif
endmodule
