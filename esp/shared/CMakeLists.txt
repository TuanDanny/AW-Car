idf_component_register(SRCS "src/protocol.cpp" "src/control.cpp" INCLUDE_DIRS "include")
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
