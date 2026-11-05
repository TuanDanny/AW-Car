# 27MHz onboard oscillator. A 0.2ns engineering guardband, NOT measured jitter.
create_clock -name clk_27m -period 37.037037 -waveform {0 18.5185185} [get_ports {clk}]
set_clock_uncertainty -setup 0.2 -to [get_clocks {clk_27m}]
set_clock_uncertainty -hold 0.2 -to [get_clocks {clk_27m}]
# All external data/reset signals are asynchronous. Do not invent a shared
# launch clock with ESP32, the encoders, a pushbutton, or the external gate.
# These are transport-delay budgets, NOT synchronous input setup/hold claims.
set_max_delay -from [get_ports {arst_n rx left_out right_out motion_permit_async recovery_req_async safety_ok_async gate_fault_n_async}] 37.037037
set_min_delay -from [get_ports {arst_n rx left_out right_out motion_permit_async recovery_req_async safety_ok_async gate_fault_n_async}] 0
# Receivers are asynchronous / driver logic. Bound clock-to-pad propagation.
set_max_delay -to [get_ports {tx drv_left_in1 drv_left_in2 drv_right_in1 drv_right_in2 fpga_permit recovery_ack gate_clear leds_n[0] leds_n[1] leds_n[2] leds_n[3] leds_n[4] leds_n[5]}] 37.037037
set_min_delay -to [get_ports {tx drv_left_in1 drv_left_in2 drv_right_in1 drv_right_in2 fpga_permit recovery_ack gate_clear leds_n[0] leds_n[1] leds_n[2] leds_n[3] leds_n[4] leds_n[5]}] 0
# Retain and explicitly time raw asynchronous shutdown. No false-path waiver.
set_max_delay -from [get_ports {arst_n motion_permit_async safety_ok_async gate_fault_n_async}] -to [get_ports {drv_left_in1 drv_left_in2 drv_right_in1 drv_right_in2 fpga_permit gate_clear}] 37.037037
# An asynchronous first sampler has no synchronous setup/hold relationship.
# Scope this waiver to the FOUR D pins; stage1->stage2 and safety mask paths
# remain timed. These exact post-synthesis names are checked against the netlist.
set_false_path -from [get_ports {rx recovery_req_async left_out right_out}] -to [get_pins {core/core_0/link/receiver/meta_ff_s0/D core/core_0/control_sync/meta_ff_0_s0/D core/core_0/g_single_out.encoders/left_filter/meta_ff_0_s0/D core/core_0/g_single_out.encoders/right_filter/meta_ff_0_s0/D}]
