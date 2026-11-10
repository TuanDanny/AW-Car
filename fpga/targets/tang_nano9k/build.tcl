# Build only: no Programmer, COM, JTAG, or flash action.
set target [file normalize [file dirname [info script]]]
set root [file normalize [file join $target ../../..]]
set build [file join $root build fpga gowin]
create_project -name simplev1_nano9k -dir $build -pn GW1NR-LV9QN88PC6/I5 -device_version C -force
foreach source [lsort [glob [file join $root fpga rtl *.sv]]] {add_file $source}
add_file [file join $target simplev1_nano9k.sv]
add_file [file join $target simplev1_nano9k.cst]
add_file [file join $target simplev1_nano9k.sdc]
set_option -top_module simplev1_nano9k
set_option -verilog_std sysv2017
set_option -output_base_name simplev1_nano9k
set_option -print_all_synthesis_warning 1
set_option -cst_warn_to_error 1
set_option -timing_driven 1
set_option -gen_text_timing_rpt 1
set_option -gen_io_cst 1
set_option -gen_posp 1
set_option -gen_verilog_sim_netlist 1
set_option -show_init_in_vo 1
set_option -use_jtag_as_gpio 0
set_option -use_mspi_as_gpio 0
set_option -use_sspi_as_gpio 0
run all
