# One actual oscillator; SPI is oversampled data, not a generated clock.
create_clock -name clk_27m -period 37.037037 -waveform {0 18.5185185} [get_ports {clk}]
# Engineering margin, not a measured jitter claim.
set_clock_uncertainty -setup 0.2 -to [get_clocks {clk_27m}]
set_clock_uncertainty -hold 0.2 -to [get_clocks {clk_27m}]
# Asynchronous inputs: transport budgets, not a synchronous timing relationship.
set_max_delay -from [get_ports {arst_n spi_mosi spi_sclk spi_cs_n enc_left enc_right}] 37.037037
set_min_delay -from [get_ports {arst_n spi_mosi spi_sclk spi_cs_n enc_left enc_right}] 0
# Bound output routing, including MISO (< one SPI half-cycle of 500ns).
set_max_delay -to [get_ports {spi_miso drv_left_in1 drv_left_in2 drv_right_in1 drv_right_in2 leds_n[0] leds_n[1] leds_n[2] leds_n[3] leds_n[4] leds_n[5]}] 37.037037
set_min_delay -to [get_ports {spi_miso drv_left_in1 drv_left_in2 drv_right_in1 drv_right_in2 leds_n[0] leds_n[1] leds_n[2] leds_n[3] leds_n[4] leds_n[5]}] 0
# Do not waive the asynchronous S2-to-driver shutdown path.
set_max_delay -from [get_ports {arst_n}] -to [get_ports {drv_left_in1 drv_left_in2 drv_right_in1 drv_right_in2}] 37.037037
# No blanket false paths. Only the D pins of the five asynchronous first samplers
# are excepted; all second stages and internal/output/reset paths remain timed.
# This Gowin build packs first samplers into I/O FFs and names them *_s1.
set_false_path -from [get_ports {spi_mosi spi_sclk spi_cs_n enc_left enc_right}] -to [get_pins {core/link/mosi_meta_s1/D core/link/sclk_meta_s1/D core/link/cs_meta_s1/D core/left_encoder/meta_ff_s1/D core/right_encoder/meta_ff_s1/D}]
