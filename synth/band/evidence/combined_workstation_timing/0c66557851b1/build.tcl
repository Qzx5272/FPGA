set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module offline_workstation_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 1
add_file impl/gwsynthesis/combined_workstation.vg
set_option -output_base_name combined_workstation
add_file stage.sdc
add_file stage.cst
run pnr
