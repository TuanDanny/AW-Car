#include "mcp_server.h"
#include "runtime.h"
#include "throttle.hpp"
#include "board.h"
#include "audio_codec.h"

namespace brain {
void AddTools(McpServer& mcp) {
    mcp.AddTool("self.car.move",
        "控制小车：forward前进、backward后退、left原地左转、right原地右转；"
        "forward_left前进左转弯、forward_right前进右转弯、backward_left后退且车头向左转、backward_right后退且车头向右转；"
        "pivot_left左侧PWM为零右侧前进、pivot_right右侧PWM为零左侧前进；零PWM不保证制动锁轮。转弯内侧油门为外侧一半，不保证实际半径或角度。"
        "用户只说左转或右转且未指定前进后退时，保留left/right原地转；明确前进转弯才使用forward_left/forward_right。"
        "speed是与网页相同的油门百分比，范围0到100，未指定默认20。用户说百分之几就传几，每条指令独立。"
        "duration毫秒100到3000默认3000（三秒），用户指定时间则使用指定值。"
        "须在AI模式开始新听音会话；排队成功不代表车已运动。",
        PropertyList({Property("action", kPropertyTypeString).SetMaxLength(16),
            Property("speed", kPropertyTypeInteger, kDefaultThrottlePercent, 0, 100),
            Property("duration", kPropertyTypeInteger, simple::kAiDefaultDurationMs, 100, 3000)}),
        [](const PropertyList& p) -> ToolResult {
            const auto& action = p["action"].value<std::string>();
            simple::Action command;
            if (!simple::parse_action(action.c_str(), command) || command == simple::Action::Neutral)
                return std::unexpected("unknown movement action; use self.car.stop to stop");
            const int duty_percent = ThrottleToDutyPercent(p["speed"].value<int>());
            if (!Runtime::Get().Move(p.driving_context(), command,
                    duty_percent, p["duration"].value<int>()))
                return std::unexpected("Driving context expired/unavailable; select AI and explicitly start fresh listening");
            return std::string(R"({"queued":true,"hardware_ack":false})");
        });
    mcp.AddTool("self.car.stop", "立即请求停车并切换手动模式；仍可继续聊天。", PropertyList(),
        [](const PropertyList&) -> ReturnValue {
            Runtime::Get().Stop();
            return std::string(R"({"queued":true,"hardware_ack":false})");
        });
    mcp.AddTool("self.car.get_state", "读取Motion上报模式、目标占空比及编码器计数；不推断实测车速。", PropertyList(),
        [](const PropertyList&) -> ReturnValue { return Runtime::Get().StateJson(); });
    mcp.AddTool("self.get_device_status", "读取网络和扬声器状态。", PropertyList(),
        [](const PropertyList&) -> ReturnValue { return Board::GetInstance().GetDeviceStatusJson(); });
    mcp.AddTool("self.audio_speaker.set_volume", "设置扬声器音量0到100。",
        PropertyList({Property("volume", kPropertyTypeInteger, 0, 100)}),
        [](const PropertyList& p) -> ReturnValue {
            Board::GetInstance().GetAudioCodec()->SetOutputVolume(p["volume"].value<int>());
            return true;
        });
}
} // namespace brain
