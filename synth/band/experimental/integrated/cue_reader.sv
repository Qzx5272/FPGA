module cue_reader(input clk,rst,playing,input[2:0]song,input[3:0]part,input[31:0]position,
 output reg[31:0]lookahead);
 `include "cue_ranges.vh"
 reg[39:0]rom[0:CUE_WORDS-1];initial $readmemh("score_cues.mem",rom);
 reg[6:0]key;reg[11:0]base,size,index;reg[39:0]word;reg[1:0]settle;
 wire[23:0]description=range_info({song,part});
 wire[23:0]distance=word[39:16]>position?word[39:16]-position:0;
 always @(posedge clk)begin
  word<=rom[base+index];
  if(rst)begin key<=127;base<=0;size<=0;index<=0;settle<=2;lookahead<=0;end
  else if(key!={song,part})begin key<={song,part};{base,size}<=description;index<=0;settle<=2;lookahead<=0;end
  else if(!playing&&index!=0)begin index<=0;settle<=2;end
  else if(settle!=0)settle<=settle-1'b1;
  else if(index<size&&playing&&position>word[39:16]+4)begin index<=index+1'b1;settle<=2;end
  else if(index<size)lookahead<={1'b1,word[15:12],word[11:5],word[4:0],distance>65024?7'd127:distance[15:9],index[7:0]};
  else lookahead<=0;
 end
endmodule
