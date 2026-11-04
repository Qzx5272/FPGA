module coefficient_rom(input clk,input[4:0]row,input[3:0]column,output reg[31:0]matrix_word,flat_word);
 reg[31:0]matrix[0:16][0:9];reg[31:0]flat[0:169];
 initial begin $readmemh("coeffs.mem",matrix);$readmemh("coeffs.mem",flat);end
 always @(posedge clk)begin matrix_word<=matrix[row][column];flat_word<=flat[row*10+column];end
endmodule
