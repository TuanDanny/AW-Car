import test from "node:test";
import assert from "node:assert/strict";
import { InputTracker, target, actions } from "./control.mjs";
test("all six directions at 0/30/100 percent", () => {
    for (const p of [0, 30, 100]) {
        const expected = [
            [2 * p, 0],
            [-2 * p, 0],
            [2 * p, 10 * p],
            [2 * p, -10 * p],
            [0, 10 * p],
            [0, -10 * p],
        ];
        actions.forEach((a, i) => assert.deepEqual(target(a, p), expected[i]));
    }
    assert.deepEqual(target(null, 30), [0, 0]);
    assert.throws(() => target("forward", 101));
    assert.throws(() => target("forward", NaN));
});
test("last press wins, no resurrection and autorepeat ignored", () => {
    const i = new InputTracker();
    assert(i.press("W", "forward"));
    assert(i.press("A", "left"));
    assert(!i.press("W", "forward"));
    assert.equal(i.action, "left");
    assert(!i.release("W"));
    assert(i.release("A"));
    assert.equal(i.action, null);
    assert(i.press("S", "backward"));
    i.clear();
    assert.equal(i.active, null);
    assert.equal(i.held.size, 0);
});
test("releasing new key never restores old held key", () => {
    const i = new InputTracker();
    i.press(1, "forward");
    i.press(2, "spin_right");
    i.release(2);
    assert.equal(i.action, null);
    assert(!i.press(1, "forward"));
    i.release(1);
    assert(i.press(1, "forward"));
});
