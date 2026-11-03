import { InputTracker, keyActions, target } from "./control.mjs";
const $ = (id) => document.getElementById(id),
    input = new InputTracker();
let ws = null,
    state = null,
    seq = 0,
    events = [],
    power = false,
    staleTimer = null,
    lastStatus = 0,
    localMode = "Manual";
const text = (id, value) => {
    $(id).textContent = value;
};
function log(message) {
    events.unshift({
        at: new Date().toLocaleTimeString("vi-VN"),
        message: String(message),
    });
    events.length = Math.min(events.length, 100);
    $("events").replaceChildren(
        ...events.map((e) => {
            const li = document.createElement("li"),
                t = document.createElement("time"),
                s = document.createElement("span");
            t.textContent = e.at;
            s.textContent = e.message;
            li.append(t, s);
            return li;
        }),
    );
}
function send(type, data = {}) {
    if (ws?.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify({ type, seq: ++seq, ...data }));
    return true;
}
function clearInput() {
    input.clear();
    document
        .querySelectorAll("[data-action]")
        .forEach((b) => b.classList.remove("pressed"));
}
function ready() {
    return (
        ws?.readyState === WebSocket.OPEN &&
        state?.authorized &&
        state.mode === "Manual" &&
        performance.now() - lastStatus < 350
    );
}
function move() {
    if (!ready()) return;
    const [v, w] = target(
        input.action,
        Number($("speed").value),
        state.v_max ?? 200,
        state.omega_max ?? 1000,
    );
    send("MOVE", {
        epoch: state.epoch,
        challenge: state.challenge,
        v_mm_s: v,
        omega_mrad_s: w,
        ttl_ms: 120,
        deadman: input.action !== null,
    });
}
function stop() {
    clearInput();
    send("STOP");
    text("feedback", "Đã gửi DỪNG; chờ Motion xác nhận.");
}
function press(id, action) {
    if (!ready()) return;
    if (input.press(id, action)) {
        document
            .querySelectorAll("[data-action]")
            .forEach((b) =>
                b.classList.toggle(
                    "pressed",
                    b.dataset.action === input.action,
                ),
            );
        move();
    }
}
function release(id) {
    if (input.release(id)) {
        clearInput();
        move();
    }
}
function loseFocus() {
    clearInput();
    if (state?.mode === "Manual" && state.authorized) stop();
}
function render(s) {
    const previous = state;
    state = s;
    localMode = s.mode;
    lastStatus = performance.now();
    if (
        !s.authorized ||
        previous?.epoch !== s.epoch ||
        previous?.mode !== s.mode
    )
        clearInput();
    $("manual").classList.toggle("selected", s.mode === "Manual");
    $("ai").classList.toggle("selected", s.mode === "AI");
    $("manual").setAttribute("aria-pressed", String(s.mode === "Manual"));
    $("ai").setAttribute("aria-pressed", String(s.mode === "AI"));
    text("mode-title", s.mode);
    text(
        "permission",
        s.authorized
            ? "Đã cho phép chạy"
            : s.clearing
              ? "Đang yêu cầu xóa lỗi · chưa cho phép chạy"
            : s.reason === "arming"
              ? "Đang xin phép Motion"
              : "Chưa cho phép chạy",
    );
    $("permission").classList.toggle("ready", s.authorized);
    text(
        "mode-hint",
        s.mode === "Manual"
            ? "Giữ nút để chạy. Nhả nút về 0. Nút mới thay nút cũ."
            : "Nói với Xiaozhi bằng tiếng Trung. Mỗi hành động mặc định 1 giây; quyền AI tối đa 5 phút.",
    );
    document
        .querySelectorAll("[data-action]")
        .forEach((b) => (b.disabled = !(s.authorized && s.mode === "Manual")));
    $("speed").disabled = s.mode !== "Manual";
    $("arm").disabled =
        s.authorized ||
        s.clearing ||
        s.switching ||
        s.motion_state !== 0 ||
        s.telemetry_age_ms < 0 ||
        s.telemetry_age_ms >= 150 ||
        (s.mode === "AI" && !s.ai_online);
    $("clear-fault").disabled = s.authorized || s.clearing ||
        !(s.motion_state === 3 || s.fault_flags) ||
        s.telemetry_age_ms < 0 || s.telemetry_age_ms >= 150;
    text("target-v", `${s.v} mm/s`);
    text("target-w", `${s.omega} mrad/s`);
    text(
        "action-status",
        s.mode === "AI"
            ? `Quyền còn ${(s.ai_remaining_ms / 1000).toFixed(0)} s · Hành động còn ${(s.action_remaining_ms / 1000).toFixed(1)} s`
            : input.action
              ? "Đang giữ điều khiển"
              : "Chưa có hành động",
    );
    const fresh = s.telemetry_age_ms >= 0 && s.telemetry_age_ms < 150;
    text(
        "motion-state",
        fresh
            ? ["DISARMED", "ARMING", "ARMED", "FAULT"][s.motion_state]
            : "Mất phản hồi / dữ liệu cũ",
    );
    $("motion-dot").classList.toggle("online", fresh);
    const display = (v, unit) =>
        fresh && v !== null && v !== undefined
            ? `${v} ${unit}`
            : "Chưa có dữ liệu";
    text("v-est", display(s.v_est_mm_s, "mm/s"));
    text("w-est", display(s.omega_est_mrad_s, "mrad/s"));
    text("battery", display(s.battery_mv, "mV"));
    text(
        "age",
        s.telemetry_age_ms < 0 ? "Chưa có dữ liệu" : `${s.telemetry_age_ms} ms`,
    );
    text(
        "fault",
        fresh
            ? "0x" + s.fault_flags.toString(16).padStart(4, "0")
            : "Chưa có dữ liệu",
    );
    text("applied", `${s.last_req_seq ?? "—"} / ${s.applied_seq ?? "—"}`);
    text(
        "clock",
        s.mode === "AI"
            ? `AI ${s.ai_online ? "online" : "offline"}`
            : "Manual · mạng local",
    );
    text(
        "environment",
        s.data_source === "mock"
            ? "Motion giả lập · chưa nối xe"
            : "ESP32-S3 Brain",
    );
    if (s.rgb) {
        power = s.rgb.power;
        text(
            "rgb-state",
            s.rgb.known === false
                ? "Chưa biết trạng thái"
                : power
                  ? "Đang bật"
                  : "Đang tắt",
        );
        text("rgb-power", power ? "Tắt đèn" : "Bật đèn");
    }
    if (s.web_uart_p95_us != null)
        text(
            "stats",
            `Brain → UART p95: ${(s.web_uart_p95_us / 1000).toFixed(2)} ms · cửa sổ gần nhất`,
        );
    if (s.chat_state) text("chat-state", s.chat_state);
    if (previous?.reason !== s.reason) log(`Trạng thái: ${s.reason}`);
}
function openSocket() {
    clearInput();
    state = null;
    seq = 0;
    ws = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`,
    );
    ws.onopen = () => {
        text("connection", "Đã kết nối Brain");
        $("login").hidden = true;
        $("dashboard").hidden = false;
        log("Dashboard đã kết nối; không phát lại lệnh lái trước đó.");
    };
    ws.onmessage = (ev) => {
        let m;
        try {
            m = JSON.parse(ev.data);
        } catch {
            return;
        }
        if (m.type === "STATUS") render(m);
        else if (m.type === "CHALLENGE") {
            if (state && m.epoch === state.epoch) state.challenge = m.challenge;
        } else if (m.type === "ACK") {
            if (m.result !== "OK") {
                text("feedback", `Brain từ chối: ${m.result}`);
                if (m.result === "STALE") clearInput();
            } else
                text(
                    "feedback",
                    "Brain đã nhận yêu cầu; xem phản hồi Motion bên phải.",
                );
        } else if (m.type === "EVENT") {
            log(`${m.kind}: ${m.text}`);
            if (m.kind === "stt") text("stt", m.text);
            if (m.kind === "reply") text("reply", m.text);
        }
    };
    ws.onclose = () => {
        clearInput();
        state = null;
        text("permission", "Chưa xác nhận quyền chạy · mất kết nối");
        $("permission").classList.remove("ready");
        $("arm").disabled = true;
        $("clear-fault").disabled = true;
        text("connection", "Mất kết nối · bấm Kết nối để mở lại");
        $("login").hidden = false;
        $("dashboard").hidden = true;
        text(
            "login-message",
            "Kết nối đã đóng hoặc đang có dashboard khác. Không tự kết nối/lái lại.",
        );
    };
    ws.onerror = () =>
        text(
            "login-message",
            "Không mở được WebSocket. Có thể dashboard khác đang kết nối.",
        );
}
$("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    text("login-message", "");
    try {
        const r = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pin: $("pin").value }),
        });
        $("pin").value = "";
        if (!r.ok)
            throw new Error(
                r.status === 409
                    ? "Dashboard khác đang kết nối."
                    : "Mã điều khiển không đúng hoặc thử quá nhanh.",
            );
        openSocket();
    } catch (err) {
        text("login-message", err.message);
    }
});
$("show-pin").onclick = () =>
    fetch("/api/pairing", { method: "POST" }).then(() =>
        text(
            "login-message",
            "Xem mã trên OLED; giả lập in mã trong terminal.",
        ),
    );
$("stop").onclick = stop;
$("arm").onclick = () => {
    clearInput();
    send("ARM", { epoch: state?.epoch });
};
$("clear-fault").onclick = () => {
    clearInput();
    send("CLEAR_FAULT", { epoch: state?.epoch });
    text("feedback", "Đã yêu cầu xóa lỗi. Thành công vẫn phải bấm Cho phép lại.");
};
for (const [id, mode] of [
    ["manual", "Manual"],
    ["ai", "AI"],
])
    $(id).onclick = () => {
        if (state?.mode === mode) return;
        clearInput();
        send("SET_MODE", { mode, epoch: state?.epoch });
    };
for (const b of document.querySelectorAll("[data-action]")) {
    b.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        b.setPointerCapture(e.pointerId);
        press(`p${e.pointerId}`, b.dataset.action);
    });
    for (const name of ["pointerup", "pointercancel", "lostpointercapture"])
        b.addEventListener(name, (e) => release(`p${e.pointerId}`));
}
window.addEventListener("keydown", (e) => {
    if (e.target.closest('input,textarea,select,[contenteditable="true"]'))
        return;
    if (e.code === "Space") {
        e.preventDefault();
        if (!e.repeat) stop();
        return;
    }
    if (keyActions[e.code]) {
        e.preventDefault();
        if (!e.repeat) press(e.code, keyActions[e.code]);
    }
});
window.addEventListener("keyup", (e) => release(e.code));
window.addEventListener("blur", loseFocus);
window.addEventListener("pagehide", () => {
    loseFocus();
    ws?.close();
});
document.addEventListener("visibilitychange", () => {
    if (document.hidden) loseFocus();
});
$("speed").oninput = () => {
    text("speed-value", `${$("speed").value}%`);
    if (input.action) move();
};
$("rgb-power").onclick = () => send("RGB", { on: !power });
for (const b of document.querySelectorAll("[data-rgb]"))
    b.onclick = () => {
        const [r, g, bv] = b.dataset.rgb.split(",").map(Number);
        send("RGB", { r, g, b: bv });
    };
$("rgb-color").onchange = (e) => {
    const v = parseInt(e.target.value.slice(1), 16);
    send("RGB", { r: v >> 16, g: (v >> 8) & 255, b: v & 255 });
};
$("chat").onclick = () => send("CHAT_TOGGLE");
$("clear-log").onclick = () => {
    events = [];
    $("events").replaceChildren();
};
$("wifi-form").onsubmit = async (e) => {
    e.preventDefault();
    if (state?.motion_state !== 0 || state.authorized) {
        text("feedback", "DỪNG và đợi DISARMED trước khi đổi Wi-Fi.");
        return;
    }
    const f = new FormData(e.target);
    const r = await fetch("/api/wifi", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.fromEntries(f)),
    });
    text("feedback", r.ok ? "Đã lưu yêu cầu Wi-Fi." : "Không lưu được Wi-Fi.");
    e.target.querySelector("[name=password]").value = "";
};
setInterval(() => {
    if (document.hidden) return;
    if (ready()) move();
    else if (ws?.readyState === WebSocket.OPEN) send("HEARTBEAT");
}, 50);
staleTimer = setInterval(() => {
    if (state && performance.now() - lastStatus > 350) {
        clearInput();
        if (state.mode === "Manual") send("STOP");
        state.authorized = false;
        document
            .querySelectorAll("[data-action]")
            .forEach((b) => (b.disabled = true));
        text("permission", "Mất trạng thái Brain · đã khóa điều khiển");
    }
}, 100);
