idf_component_register(SRCS "management.cpp" INCLUDE_DIRS "."
    REQUIRES shared esp_https_server esp_netif esp_wifi esp_timer esp_app_format
        espressif__mdns espressif__cjson)
if(NOT CMAKE_BUILD_EARLY_EXPANSION)
    if(NOT DEFINED SIMPLE_MGMT_KEY_DIR)
        message(FATAL_ERROR "Build with utils/build_esp.py to provision the local management key")
    endif()
    target_include_directories(${COMPONENT_LIB} PRIVATE "${SIMPLE_MGMT_KEY_DIR}")
    target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
endif()
