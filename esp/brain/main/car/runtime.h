#pragma once
#include <atomic>
#include <mutex>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include "ai_context.hpp"

class StaNetwork;
class StatusLed;
namespace brain {
class Runtime {
public:
    static Runtime& Get() { static Runtime instance; return instance; }
    void Start(StaNetwork* network, StatusLed* led);
    DriveContext BeginExplicit();
    void BindSession(const DriveContext& context, const std::string& session);
    DriveContext Capture(const std::string& session);
    bool Move(const DriveContext& context, simple::Action action, int speed, int duration_ms);
    void Stop();
    std::string StateJson();
    void Diagnostics(char* output,size_t capacity);
    void SetCloud(bool connected);
    void AudioClosed(bool cloud_closed);
    void SetAudio(bool listening, bool speaking);
    void Invalidate();
private:
    struct PendingMove { DriveContext context; simple::AiMove move; };
    void Run();
    void Receive(const simple::Frame& frame);
    bool Send(simple::Frame frame);
    std::mutex mutex_;
    AiContext context_;
    std::atomic<bool> cloud_{false}, listening_{false}, speaking_{false}, stop_pending_{false};
    QueueHandle_t moves_{};
    TaskHandle_t task_{};
    StaNetwork* network_{};
    StatusLed* led_{};
    uint16_t sequence_{};
};
} // namespace brain
