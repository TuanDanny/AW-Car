# Exactly one board and only the audio/OLED/cloud source it uses.
set(sources application.cc assets.cc device_state_machine.cc main.cc mcp_server.cc
    ota.cc settings.cc system_info.cc
    audio/audio_codec.cc audio/audio_service.cc audio/audio_debugger.cc
    audio/codecs/no_audio_codec.cc audio/demuxer/ogg_demuxer.cc
    audio/engines/afe_audio_engine.cc audio/wake_words/custom_wake_word.cc
    audio/wake_words/wake_word_audio_cache.cc notify/notify_player.cc
    boards/common/board.cc boards/common/button.cc
    boards/aw-car/board.cc boards/aw-car/sta_network.cc boards/aw-car/status_led.cc
    car/runtime.cc car/tools.cc
    display/display.cc display/text_glyph.cc display/oled_display.cc
    display/lvgl_display/lvgl_display.cc display/lvgl_display/lvgl_font.cc
    display/lvgl_display/lvgl_theme.cc display/lvgl_display/lvgl_image.cc
    display/lvgl_display/dynamic_glyph_cache.cc display/lvgl_display/emoji_collection.cc
    protocols/protocol.cc protocols/mqtt_protocol.cc protocols/websocket_protocol.cc
    protocols/text_glyph_payload.cc)
file(GLOB lang_sounds "assets/locales/zh-CN/*.ogg")
file(GLOB common_sounds "assets/common/*.ogg")
idf_component_register(SRCS ${sources} EMBED_FILES ${lang_sounds} ${common_sounds}
    INCLUDE_DIRS . audio audio/demuxer display display/lvgl_display protocols
        boards/common boards/aw-car
    PRIV_REQUIRES shared xiaozhi_network ssid_store esp_wifi esp_netif esp_event
        esp_timer esp_driver_gpio esp_driver_uart esp_driver_i2c esp_driver_i2s pthread
        esp_lcd esp_pm esp_psram app_update spi_flash nvs_flash efuse
        esp_app_format mbedtls esp-sr esp_audio_codec esp_audio_effects
        esp_codec_dev esp_lvgl_port lvgl button led_strip xiaozhi-fonts espressif__cjson)
if(NOT CMAKE_BUILD_EARLY_EXPANSION)
    if(DEFINED SIMPLE_BUILD_ID)
        target_compile_definitions(${COMPONENT_LIB} PRIVATE SIMPLE_BUILD_ID="${SIMPLE_BUILD_ID}")
    endif()
    target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_23)
    target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-missing-field-initializers)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE HAVE_LVGL=1
        BOARD_TYPE="aw-car-simplev1" BOARD_NAME="aw-car-simplev1" BOARD_MANUFACTURER="AW-Car"
        BUILTIN_TEXT_FONT=font_noto_sans_basic_14_1
        BUILTIN_ICON_FONT=font_material_symbols_14_1 TEXT_FONT_SIZE=14 TEXT_FONT_BPP=1)
    execute_process(COMMAND "${PYTHON}" "${PROJECT_DIR}/scripts/gen_lang.py"
        --language zh-CN --output "${CMAKE_CURRENT_SOURCE_DIR}/assets/lang_config.h"
        COMMAND_ERROR_IS_FATAL ANY)
    idf_component_get_property(fonts_dir 78__xiaozhi-fonts COMPONENT_DIR)
    idf_component_get_property(sr_dir espressif__esp-sr COMPONENT_DIR)
    add_custom_command(OUTPUT "${CMAKE_BINARY_DIR}/generated_assets.bin"
        COMMAND "${PYTHON}" "${PROJECT_DIR}/scripts/build_default_assets.py"
            --sdkconfig "${SDKCONFIG}" --output "${CMAKE_BINARY_DIR}/generated_assets.bin"
            --builtin_text_font font_noto_sans_basic_14_1
            --noto_fonts_path "${fonts_dir}" --esp_sr_model_path "${sr_dir}/model"
            --max_size 0x800000
        DEPENDS "${SDKCONFIG}" "${PROJECT_DIR}/scripts/build_default_assets.py"
        VERBATIM)
    add_custom_target(brain_assets ALL DEPENDS "${CMAKE_BINARY_DIR}/generated_assets.bin")
    esptool_py_flash_to_partition(flash assets "${CMAKE_BINARY_DIR}/generated_assets.bin")
endif()
