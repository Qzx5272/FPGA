set here [file dirname [file normalize [info script]]]
file mkdir "$here/build/delay"
cd "$here/build/delay"
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module stereo_delay
set_option -verilog_std v2001
add_file "$here/rtl/stereo_delay.v"
set_option -output_base_name band_delay
run syn
