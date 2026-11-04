set here [file dirname [file normalize [info script]]]
file mkdir "$here/build/renderer"
cd "$here/build/renderer"
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module band_renderer
set_option -verilog_std v2001
add_file "$here/rtl/band_renderer.v"
add_file "$here/../rtl/hq_sine_quarter.v"
set_option -output_base_name band_renderer
run syn
