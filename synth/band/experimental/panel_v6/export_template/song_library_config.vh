localparam LIBRARY_WORDS=8463,LIBRARY_SONGS=3;
function[127:0]library_description;input[7:0]song;begin case(song)
0:library_description={32'd0,32'd8175,32'd4608000,32'd3996663517};
1:library_description={32'd8175,32'd192,32'd792000,32'd1715341427};
2:library_description={32'd8367,32'd96,32'd408000,32'd1033968761};
default:library_description=0;endcase end endfunction
