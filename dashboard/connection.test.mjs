import test from "node:test";
import assert from "node:assert/strict";
import { DashboardLink, networkStatus } from "./connection.mjs";

test("Wi-Fi IP and Xiaozhi session are independent; old disconnect reason is historical", () => {
    const s = {network: {sta_state: "online", ip_valid: true, sta_reason: 202, sta_ip: "192.0.2.2"}, ai_online: false};
    assert.match(networkStatus(s).wifi, /Đã kết nối/);
    assert.match(networkStatus(s).ai, /chưa kết nối dịch vụ/);
    assert.equal(networkStatus(s).tone, "online");
    s.ai_online = true;
    assert.match(networkStatus(s).ai, /đã kết nối dịch vụ/);
    assert.equal(networkStatus(s, false).tone, "unknown");
});
test("Wi-Fi distinguishes association, DHCP, auth failure and retry countdown", () => {
    const s = {network: {sta_state: "connecting", ip_valid: false}};
    assert.match(networkStatus(s).wifi, /Đang kết nối/);
    s.network.sta_state = "dhcp";
    assert.match(networkStatus(s).wifi, /địa chỉ IP/);
    s.network = {sta_state: "cooldown", sta_reason: 202, retry_in_ms: 1001};
    assert.match(networkStatus(s).detail, /từ chối xác thực.*2 s/);
    assert.match(networkStatus(s).ai, /chờ Wi-Fi/);
    s.network.sta_reason = 201;
    assert.match(networkStatus(s).detail, /Không tìm thấy mạng/);
});
const state = (epoch = 1, authorized = false, mode = "Manual") => ({
    epoch,
    authorized,
    mode,
});
test("new/reconnected socket never accepts an old Manual ARM", () => {
    const x = new DashboardLink();
    x.opened(0);
    x.status(state(1, true), 1);
    assert.equal(x.drive(state(1, true), 1), false);
    x.arm(state());
    x.status(state(), 2);
    x.status(state(1, true), 3);
    assert.equal(x.drive(state(1, true), 3), true);
    x.disconnected();
    x.opened(4);
    x.status(state(1, true), 5);
    assert.equal(x.drive(state(1, true), 5), false);
});
test("stale STATUS sends one safety STOP per epoch, no 100ms flood", () => {
    const x = new DashboardLink();
    x.opened(0);
    x.status(state(1, true), 0);
    x.arm(state());
    let stops = 0;
    for (let now = 350; now < 10000; now += 100) {
        if (x.check(now) && x.safetyStop(state(1, true))) ++stops;
    }
    assert.equal(stops, 1);
    assert.equal(x.state, "Degraded");
    x.status(state(1, true), 10000);
    assert.equal(x.drive(state(1, true), 10000), false);
    x.status(state(2), 10001);
    assert.equal(x.safetyStop(state(2)), true);
});
test("blur visibility and pagehide coalesce; AI socket loss is not a motor ACK", () => {
    const x = new DashboardLink();
    x.opened(0);
    x.status(state(1, true), 0);
    assert.equal(x.safetyStop(state(1, true)), true);
    assert.equal(x.safetyStop(state(1, true)), false);
    assert.equal(x.safetyStop(state(1, true)), false);
    assert.equal(x.safetyStop(state(1, true, "AI")), false);
    x.disconnected(true);
    assert.equal(x.state, "Unauthorized");
    assert.equal(x.open, false);
});
test("CHALLENGE cannot substitute a fresh STATUS", () => {
    const x = new DashboardLink();
    x.opened(0);
    x.status(state(1, true), 1);
    x.arm(state());
    assert.equal(x.drive(state(1, true), 350), true);
    assert.equal(x.drive(state(1, true), 351), false);
});
