export const actions = [
    "forward",
    "backward",
    "left",
    "right",
    "spin_left",
    "spin_right",
];
export const keyActions = {
    KeyW: "forward",
    KeyS: "backward",
    KeyA: "left",
    KeyD: "right",
    KeyQ: "spin_left",
    KeyE: "spin_right",
};
export function target(action, pct, vmax = 200, wmax = 1000) {
    if (!Number.isInteger(pct) || pct < 0 || pct > 100)
        throw new Error("speed");
    const v = Math.round((vmax * pct) / 100),
        w = Math.round((wmax * pct) / 100);
    switch (action) {
        case null:
            return [0, 0];
        case "forward":
            return [v, 0];
        case "backward":
            return [-v, 0];
        case "left":
            return [v, w];
        case "right":
            return [v, -w];
        case "spin_left":
            return [0, w];
        case "spin_right":
            return [0, -w];
        default:
            throw new Error("action");
    }
}
export class InputTracker {
    constructor() {
        this.held = new Set();
        this.active = null;
        this.action = null;
    }
    press(id, action) {
        if (this.held.has(id)) return false;
        if (!actions.includes(action)) throw new Error("action");
        this.held.add(id);
        this.active = id;
        this.action = action;
        return true;
    }
    release(id) {
        this.held.delete(id);
        if (this.active !== id) return false;
        this.active = null;
        this.action = null;
        return true;
    }
    clear() {
        this.held.clear();
        this.active = null;
        this.action = null;
    }
}
