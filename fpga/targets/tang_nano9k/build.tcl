# Build only. This script contains no Programmer/JTAG/COM/flash command.
set target [file normalize [file dirname [info script]]]
set root [file normalize [file join $target ../../..]]
set build [file join $root build tang-nano9k gowin]
if {[info exists ::env(AWCAR_BUILD_DIR)]} {set build [file normalize $::env(AWCAR_BUILD_DIR)]}
set allowed [string tolower [file normalize [file join $root build]]]
if {[string first "$allowed/" [string tolower $build]] != 0} {
    error "Generated Gowin project must stay below this checkout's build directory"
}
create_project -name aw_car_nano9k -dir $build -pn GW1NR-LV9QN88PC6/I5 -device_version C -force
proc rtl_sources {dir} {
    set sources [glob -nocomplain -directory $dir *.sv]
    foreach child [glob -nocomplain -types d -directory $dir *] {
        set sources [concat $sources [rtl_sources $child]]
    }
    return [lsort $sources]
}
foreach source [rtl_sources [file join $root fpga rtl]] {add_file $source}
add_file [file join $target aw_car_nano9k.sv]
add_file [file join $target aw_car_nano9k.cst]
add_file [file join $target aw_car_nano9k.sdc]
set_option -top_module aw_car_nano9k
set_option -verilog_std sysv2017
set_option -output_base_name aw_car_nano9k
set_option -print_all_synthesis_warning 1
set_option -cst_warn_to_error 1
set_option -timing_driven 1
set_option -gen_text_timing_rpt 1
set_option -gen_io_cst 1
set_option -gen_posp 1
set_option -gen_verilog_sim_netlist 1
set_option -show_init_in_vo 1
# Keep JTAG, configuration and onboard flash pins dedicated.
set_option -use_jtag_as_gpio 0
set_option -use_mspi_as_gpio 0
set_option -use_sspi_as_gpio 0
set flow all
if {[info exists ::env(AWCAR_GOWIN_FLOW)]} {set flow $::env(AWCAR_GOWIN_FLOW)}
if {$flow ni {syn all}} {error "AWCAR_GOWIN_FLOW must be syn or all"}
run $flow
