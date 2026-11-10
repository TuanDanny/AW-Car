#include "mcp_server.h"
#include "runtime.h"
#include "board.h"
#include "audio_codec.h"

namespace brain {
void AddTools(McpServer& mcp) {
    mcp.AddTool("self.car.move",
        "控制小车：action只能是forward前进、backward后退、left原地左转、right原地右转。"
        "speed百分比0到100默认30；duration毫秒100到3000默认3000（三秒），用户指定时间则使用指定值。"
        "须在AI模式开始新听音会话；排队成功不代表车已运动。",
        PropertyList({Property("action", kPropertyTypeString).SetMaxLength(8),
            Property("speed", kPropertyTypeInteger, 30, 0, 100),
            Property("duration", kPropertyTypeInteger, simple::kAiDefaultDurationMs, 100, 3000)}),
        [](const PropertyList& p) -> ToolResult {
            const auto& action = p["action"].value<std::string>();
            simple::Action command;
            if (action == "forward") command = simple::Action::Forward;
            else if (action == "backward") command = simple::Action::Backward;
            else if (action == "left") command = simple::Action::Left;
            else if (action == "right") command = simple::Action::Right;
            else return std::unexpected("action must be forward/backward/left/right");
            if (!Runtime::Get().Move(p.driving_context(), command,
                    p["speed"].value<int>(), p["duration"].value<int>()))
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
