// Transport health never renews the independent 120/150ms motion lease.
export function networkStatus(status, fresh = true) {
    const n = status?.network;
    if (!fresh || !n) return {
        wifi: "Chưa có trạng thái Wi-Fi mới", detail: "Chờ STATUS từ Brain.",
        ai: "Chưa có trạng thái Xiaozhi mới", tone: "unknown",
    };
    const connected = n.sta_state === "online" && n.ip_valid === true;
    const phase = {
        no_credentials: "Chưa cấu hình Wi-Fi", waiting: "Chờ kết nối Wi-Fi",
        connecting: "Đang kết nối Wi-Fi", dhcp: "Đang lấy địa chỉ IP",
        backoff: "Chưa kết nối Wi-Fi", cooldown: "Đang chờ thử lại Wi-Fi",
    };
    const reasons = {201: "Không tìm thấy mạng", 202: "Wi-Fi từ chối xác thực", 204: "Hết thời gian bắt tay"};
    const retry = n.retry_in_ms > 0 ? ` · thử lại sau ${Math.ceil(n.retry_in_ms / 1000)} s` : "";
    const failed = ["backoff", "cooldown"].includes(n.sta_state);
    return {
        wifi: connected ? `Đã kết nối Wi-Fi${n.sta_ssid ? " · " + n.sta_ssid : ""}` : phase[n.sta_state] ?? "Chưa kết nối Wi-Fi",
        detail: connected
            ? `IP ${n.sta_ip || "đã nhận"}${n.rssi == null ? "" : " · " + n.rssi + " dBm"}`
            : `${failed ? reasons[n.sta_reason] ?? "Kết nối chưa thành công" : "Dashboard AW-CAR vẫn dùng được"}${retry}`,
        ai: !connected ? "Xiaozhi: chờ Wi-Fi" : status.ai_online
            ? "Xiaozhi: đã kết nối dịch vụ" : "Xiaozhi: chưa kết nối dịch vụ · nhấn Nghe để thử",
        tone: connected ? "online" : failed ? "warning" : "waiting",
    };
}

export class DashboardLink {
    constructor() {
        this.disconnected();
    }
    opened(now) {
        this.state = "Degraded";
        this.open = true;
        this.lastStatus = now;
        this.haveStatus = false;
        this.armEpoch = null;
        this.pendingArm = false;
        this.stoppedEpoch = null;
    }
    disconnected(unauthorized = false) {
        this.state = unauthorized ? "Unauthorized" : "Disconnected";
        this.open = false;
        this.haveStatus = false;
        this.armEpoch = null;
        this.pendingArm = false;
        this.stoppedEpoch = null;
    }
    status(s, now) {
        this.lastStatus = now;
        this.haveStatus = true;
        this.state = this.open ? "Connected" : this.state;
        if (
            s.mode !== "Manual" ||
            (this.armEpoch !== null && this.armEpoch !== s.epoch)
        )
            this.revoke();
        if (s.authorized) this.pendingArm = false;
        else if (!this.pendingArm) this.armEpoch = null;
    }
    arm(s) {
        this.armEpoch = s?.epoch ?? null;
        this.pendingArm = true;
    }
    revoke() {
        this.armEpoch = null;
        this.pendingArm = false;
    }
    stale(now) {
        return this.open && (!this.haveStatus || now - this.lastStatus >= 350);
    }
    check(now) {
        if (this.stale(now)) {
            this.state = "Degraded";
            this.revoke();
            return true;
        }
        return false;
    }
    drive(s, now) {
        return (
            this.open &&
            !this.stale(now) &&
            s?.mode === "Manual" &&
            s.authorized &&
            this.armEpoch === s.epoch
        );
    }
    safetyStop(s) {
        this.revoke();
        const epoch = s?.epoch ?? -1;
        if (!this.open || s?.mode !== "Manual" || this.stoppedEpoch === epoch)
            return false;
        this.stoppedEpoch = epoch;
        return true;
    }
}
