set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module fft_fixed
set_option -verilog_std sysv2017
add_file fft_fixed.v
set_option -output_base_name fft2048
run syn
