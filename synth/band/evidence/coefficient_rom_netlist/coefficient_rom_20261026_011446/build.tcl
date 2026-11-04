set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module coefficient_rom
set_option -verilog_std sysv2017
add_file coefficient_rom.sv
set_option -output_base_name coefficient_rom
run syn
