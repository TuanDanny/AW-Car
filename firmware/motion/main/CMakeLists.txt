idf_component_register(
    SRCS "app_main.cc" "runtime.cc" "console.cc" "motion_core.cc"
         "fpga_link.cc" "drive_model.cc" "../../shared/brain_motion_codec.cc"
         "../../shared/fpga_codec.cc"
    INCLUDE_DIRS "." "../../shared"
    REQUIRES esp_driver_gpio esp_driver_uart esp_driver_gptimer esp_timer
             nvs_flash esp_system esp_hw_support
)
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Werror)
