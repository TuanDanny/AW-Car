idf_component_register(SRCS "main.cpp" "runtime.cpp" "web.cpp" "network_manager.cpp"
    INCLUDE_DIRS "." REQUIRES shared management esp_driver_gpio esp_driver_spi esp_driver_uart
    esp_wifi esp_netif esp_event esp_http_server esp_timer nvs_flash espressif__cjson espressif__led_strip
    EMBED_TXTFILES "../web/index.html")
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
if(DEFINED SIMPLE_BUILD_ID)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE SIMPLE_BUILD_ID="${SIMPLE_BUILD_ID}")
endif()
