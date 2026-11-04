set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module gowin_dvi_output
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -output_base_name gowin_dvi_output
add_file impl/gwsynthesis/gowin_dvi_output.vg
add_file display.cst
add_file display.sdc
run pnr
