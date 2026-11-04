set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module board_pt8211_controls_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 1
add_file impl/gwsynthesis/pt8211_onboard.vg
set_option -output_base_name pt8211_onboard
add_file board.cst
add_file board.sdc
set_option -cst_warn_to_error 1
set_option -route_option 1
set_option -correct_hold_violation 1
run pnr
