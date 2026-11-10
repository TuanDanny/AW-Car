#include "runtime.h"
#include "application.h"
#include "config.h"
#include "sta_network.h"
#include "status_led.h"
#include <cJSON.h>
#include <driver/uart.h>
#include <esp_log.h>
#include <esp_timer.h>
#include <cstring>
#include <cstdio>

namespace brain {
namespace { constexpr auto kUart = UART_NUM_1; uint64_t Now() { return esp_timer_get_time()/1000; } }
void Runtime::Start(StaNetwork* network, StatusLed* led) {
    network_ = network;
    led_ = led;
    moves_ = xQueueCreate(1, sizeof(PendingMove));
    ESP_ERROR_CHECK(moves_ ? ESP_OK : ESP_ERR_NO_MEM);
    uart_config_t config{};
    config.baud_rate = 460800;
    config.data_bits = UART_DATA_8_BITS;
    config.parity = UART_PARITY_DISABLE;
    config.stop_bits = UART_STOP_BITS_1;
    config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    config.source_clk = UART_SCLK_DEFAULT;
    ESP_ERROR_CHECK(uart_param_config(kUart, &config));
    ESP_ERROR_CHECK(uart_set_pin(kUart, BRAIN_UART_TX, BRAIN_UART_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(kUart, 2048, 1024, 0, nullptr, 0));
    ESP_ERROR_CHECK(xTaskCreatePinnedToCore([](void* arg) {
        static_cast<Runtime*>(arg)->Run();
    }, "brain_uart1", 4096, this, 9, &task_, 1) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
    ESP_LOGI("Brain", "simplev1 UART1 460800 TX17 RX18; Brain has no drive authority in Manual");
}
DriveContext Runtime::BeginExplicit() {
    std::lock_guard lock(mutex_);
    if(updating_) return {};
    return context_.BeginExplicit(Now());
}
void Runtime::BindSession(const DriveContext& context, const std::string& session) {
    std::lock_guard lock(mutex_);
    const bool bound = context_.Bind(context, session, Now());
    ESP_LOGI("Brain", "Fresh audio session: driving context %s", bound ? "bound" : "unavailable");
}
DriveContext Runtime::Capture(const std::string& session) {
    std::lock_guard lock(mutex_);
    return context_.Capture(session, Now());
}
void Runtime::Invalidate() { std::lock_guard lock(mutex_); context_.Invalidate(); }
void Runtime::SetCloud(bool connected) {
    cloud_ = connected;
    if (!connected) Invalidate();
}
void Runtime::AudioClosed(bool cloud_closed) {
    std::lock_guard lock(mutex_);
    context_.AudioClosed();
    if (cloud_closed) cloud_ = false;
}
void Runtime::SetAudio(bool listening, bool speaking) {
    listening_ = listening;
    speaking_ = speaking;
}
bool Runtime::Move(const DriveContext& context, simple::Action action, int speed, int duration_ms) {
    if (!simple::valid_action(action) || action == simple::Action::Neutral || speed < 0 || speed > 100 ||
        duration_ms < 100 || duration_ms > 3000 || !moves_) return false;
    std::lock_guard lock(mutex_);
    if (updating_ || stop_pending_ || !cloud_ || !context_.CanMove(context, Now())) return false;
    PendingMove pending{context, {context.generation, action, uint8_t(speed), uint16_t(duration_ms)}};
    const bool queued = xQueueOverwrite(moves_, &pending) == pdPASS;
    if (queued && task_) xTaskNotifyGive(task_);
    return queued;
}
void Runtime::Stop() {
    std::lock_guard lock(mutex_);
    context_.Invalidate();
    stop_pending_ = true;
    // UART worker sends STOP before any MOVE; chat/audio keeps running.
    if (moves_) xQueueReset(moves_);
    if (task_) xTaskNotifyGive(task_);
}
std::string Runtime::StateJson() {
    std::lock_guard lock(mutex_);
    const auto& s = context_.motion();
    auto* json = cJSON_CreateObject();
    cJSON_AddBoolToObject(json, "motion_fresh", context_.MotionFresh(Now()));
    cJSON_AddNumberToObject(json, "generation", s.generation);
    cJSON_AddStringToObject(json, "mode", s.mode == simple::Mode::Ai ? "ai" : "manual");
    cJSON_AddStringToObject(json, "action", simple::action_name(s.action));
    cJSON_AddNumberToObject(json, "speed", s.speed);
    cJSON_AddNumberToObject(json, "left_duty", s.left);
    cJSON_AddNumberToObject(json, "right_duty", s.right);
    cJSON_AddNumberToObject(json, "left_count", s.left_count);
    cJSON_AddNumberToObject(json, "right_count", s.right_count);
    cJSON_AddBoolToObject(json, "fpga_link", s.fpga_link);
    cJSON_AddStringToObject(json, "reason", simple::reason_name(s.reason));
    cJSON_AddStringToObject(json, "meaning", "reported targets/counters; not measured vehicle speed");
    char* text = cJSON_PrintUnformatted(json);
    std::string result = text ? text : "{}";
    cJSON_free(text); cJSON_Delete(json);
    return result;
}
void Runtime::Diagnostics(char* output,size_t capacity) {
    simple::MotionState s{};bool fresh=false;
    { std::lock_guard lock(mutex_);s=context_.motion();fresh=context_.MotionFresh(Now()); }
    std::snprintf(output,capacity,"{\"cloud\":%d,\"listening\":%d,\"speaking\":%d,\"motion_fresh\":%d,\"generation\":%lu,\"mode\":\"%s\",\"left\":%d,\"right\":%d}",
        int(cloud_.load()),int(listening_.load()),int(speaking_.load()),int(fresh),
        static_cast<unsigned long>(s.generation),s.mode==simple::Mode::Manual?"manual":"ai",s.left,s.right);
}
bool Runtime::BeginUpdate() {
    if(updating_.exchange(true)) return false;
    Stop();Application::GetInstance().StopListening();
    const auto deadline=Now()+500;
    while(stop_pending_ && Now()<deadline) vTaskDelay(pdMS_TO_TICKS(10));
    return !stop_pending_ && WorkerHealthy();
}
void Runtime::EndUpdate() { Invalidate();Stop();updating_=false; }
bool Runtime::WorkerHealthy() const {
    const auto at=worker_at_.load();return at && uint32_t(Now())-at<1000;
}
bool Runtime::Send(simple::Frame frame) {
    frame.seq = ++sequence_;
    uint8_t bytes[simple::kMaxFrame];
    const auto size = simple::encode_uart(frame, bytes, sizeof(bytes));
    size_t free = 0;
    if (!size || uart_get_tx_buffer_free_size(kUart, &free) != ESP_OK || free < size) return false;
    return uart_write_bytes(kUart, bytes, size) == int(size);
}
void Runtime::Receive(const simple::Frame& frame) {
    if (frame.type == simple::Type::MotionState) {
        simple::MotionState state;
        if (simple::parse_motion_state(frame, state)) {
            std::lock_guard lock(mutex_);
            context_.UpdateMotion(state, Now());
        }
    } else if (frame.type == simple::Type::Listen && frame.size == 1 && frame.payload[0] <= 1) {
        auto& app = Application::GetInstance();
        if (frame.payload[0]) app.StartListening(); else app.StopListening();
    } else if (frame.type == simple::Type::WifiConfig) {
        network_->Configure(frame);
    }
}
void Runtime::Run() {
    simple::UartParser parser;
    simple::Frame frame;
    uint64_t next_status = 0;
    for (;;) {
        worker_at_=uint32_t(Now());
        uint8_t bytes[256];
        const int size = uart_read_bytes(kUart, bytes, sizeof(bytes), 0);
        for (int i = 0; i < size; ++i) if (parser.push(bytes[i], frame)) Receive(frame);
        {
            std::lock_guard lock(mutex_);
            if (stop_pending_) {
                simple::Frame stop; stop.type = simple::Type::Stop;
                if (Send(stop)) stop_pending_ = false;
                if (moves_) xQueueReset(moves_);
            } else {
                PendingMove pending;
                if (xQueueReceive(moves_, &pending, 0) == pdPASS && !updating_ && cloud_ &&
                    context_.CanMove(pending.context, Now())) Send(simple::make_ai_move(0, pending.move));
            }
        }
        const auto now = Now();
        if (now >= next_status) {
            next_status = now + 200;
            simple::BrainState state;
            network_->FillState(state);
            if (cloud_) state.flags |= simple::kCloudReady;
            if (listening_) state.flags |= simple::kListening;
            if (speaking_) state.flags |= simple::kSpeaking;
            Send(simple::make_brain_state(0, state));
            led_->Observe(state.flags & simple::kWifiReady, state.flags & simple::kCloudReady,
                          state.flags & simple::kListening, state.flags & simple::kSpeaking);
        }
        // Brain keeps the tested 100 Hz RTOS configuration: 5 ms rounds down
        // to ZERO ticks there. Always block at least one tick, otherwise this
        // priority-9 worker spins and starves IDLE1/audio/display indefinitely.
        constexpr TickType_t wait_ticks = pdMS_TO_TICKS(5) > 0 ? pdMS_TO_TICKS(5) : 1;
        static_assert(wait_ticks >= 1);
        ulTaskNotifyTake(pdTRUE, wait_ticks);
    }
}
} // namespace brain
