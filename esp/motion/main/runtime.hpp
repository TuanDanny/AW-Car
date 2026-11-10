#pragma once
#include "simple/control.hpp"
#include <array>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "driver/spi_master.h"

namespace motion {
struct Snapshot {
    simple::MotionState car{};
    simple::BrainState brain{};
    simple::SpiStatus fpga{};
    bool brain_connected{};
    uint32_t uart_rx{},uart_errors{},uart_tx_errors{},spi_ok{},spi_errors{},rejected{};
    uint32_t spi_io_errors{},spi_frame_errors{},spi_ack_errors{},spi_startup{};
    uint32_t latency_count{},latency_max_us{};
    std::array<uint32_t,256> latency_us{};
};
class Runtime {
public:
    static Runtime& get();
    void start();
    void stop(simple::Reason reason=simple::Reason::Stop);
    void mode(simple::Mode mode);
    void disconnect();
    void drive(simple::Action action,uint8_t speed);
    bool listen(bool enabled);
    bool wifi(const char* ssid,size_t ssid_len,const char* password,size_t password_len);
    Snapshot snapshot();
    bool network_busy();
private:
    enum class Source { None,Manual,Ai };
    struct Pending {
        bool stop{},mode{},disconnected{},brain{};
        simple::Reason stop_reason{simple::Reason::Stop};
        simple::Mode new_mode{simple::Mode::Manual};
        Source source{Source::None};
        simple::Action action{simple::Action::Neutral};
        uint8_t speed{};
        simple::AiMove ai{};
        simple::BrainState brain_state{};
        uint64_t brain_at{},command_us{},stop_us{};
    };
    void accept(const simple::Frame& frame);
    void control_loop();
    void uart_loop();
    void log_loop();
    static void control_entry(void* self) { static_cast<Runtime*>(self)->control_loop(); }
    static void uart_entry(void* self) { static_cast<Runtime*>(self)->uart_loop(); }
    static void log_entry(void* self) { static_cast<Runtime*>(self)->log_loop(); }
    void wake();
    portMUX_TYPE mux_=portMUX_INITIALIZER_UNLOCKED;
    Pending pending_{};
    Snapshot snapshot_{};
    simple::Control core_{};
    spi_device_handle_t spi_{};
    TaskHandle_t control_task_{};
    QueueHandle_t uart_events_{},uart_out_{};
};
void start_web();
} // namespace motion
