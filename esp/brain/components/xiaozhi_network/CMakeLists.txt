idf_component_register(
    SRCS src/network_error.cc src/http_client.cc src/web_socket.cc
         src/esp/esp_network.cc src/esp/esp_ssl.cc src/esp/esp_tcp.cc
         src/esp/esp_mqtt.cc src/esp/esp_udp.cc
    INCLUDE_DIRS include
    PRIV_REQUIRES esp-tls esp_timer esp_pm pthread mqtt)
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_23)
