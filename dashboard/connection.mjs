// Transport health never renews the independent 120/150ms motion lease.
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
