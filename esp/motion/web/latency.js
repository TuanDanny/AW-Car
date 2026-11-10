// Optional observer, loaded only with #latency. No automatic movement or timers.
(() => {
  'use strict';
  const samples = { forward: [], backward: [], left: [], right: [] };
  const names = { forward: 'Tiến', backward: 'Lùi', left: 'Trái', right: 'Phải' };
  const signs = { forward: [1, 1], backward: [-1, -1], left: [-1, 1], right: [1, -1] };
  const watched = new WeakSet();
  let last = null, pending = null, incomplete = 0;
  const panel = document.createElement('section');
  panel.className = 'panel'; panel.style.marginBottom = '20px';
  const title = document.createElement('h2'); title.textContent = 'Đo bấm → STATUS xác nhận';
  const hint = document.createElement('p'); hint.className = 'sub';
  hint.textContent = 'VM ngắt. Mỗi nút giữ 0,5–1 giây, nhả 1 giây. Lặp 5–10 vòng. Số đo gồm chu kỳ STATUS 100 ms; chưa đo cạnh PWM vật lý.';
  const table = document.createElement('pre'); table.id = 'latency-readout';
  table.style.cssText = 'white-space:pre-wrap;font-size:12px;line-height:1.7';
  panel.append(title, hint, table); document.querySelector('.layout').after(panel);
  function render() {
    table.textContent = 'Hướng · N · bấm→gửi / bấm→STATUS (ms)\n' + Object.keys(samples).map(action => {
      const values = samples[action]; const v = values.at(-1);
      return names[action] + ' · ' + values.length + ' · ' + (v ? (v.dispatch_us / 1000).toFixed(2) + ' / ' + (v.confirm_us / 1000).toFixed(2) : '—');
    }).join('\n') + '\nLượt chưa xác nhận/hủy: ' + incomplete;
  }
  function cancel() { if (pending) { pending = null; ++incomplete; render(); } }
  function observe(socket, data) {
    if (data.t !== 'status') return;
    last = data;
    if (!pending) return;
    const now = performance.now(), p = pending;
    if (now - p.start > 2000 || data.generation !== p.generation || data.mode !== 'manual' || data.maintenance) { cancel(); return; }
    if (p.sent === null || !data.fpga?.connected || data.fpga.applied_seq === p.seq || (data.diag?.spi_ok ?? 0) <= p.spi) return;
    if (data.action !== p.action || data.reason !== 'active' || data.left !== p.left || data.right !== p.right) return;
    const result = { t: 'latency', action: p.action,
      dispatch_us: Math.round((p.sent - p.start) * 1000), confirm_us: Math.round((now - p.start) * 1000) };
    pending = null;
    if (samples[p.action].length < 100) samples[p.action].push(result);
    render();
    // One bounded numeric report per actual press, outside the control task.
    if (socket.readyState === WebSocket.OPEN && socket.bufferedAmount === 0) socket.send(JSON.stringify(result));
  }
  const original = WebSocket.prototype.send;
  WebSocket.prototype.send = function(payload) {
    if (!watched.has(this)) {
      watched.add(this);
      this.addEventListener('message', event => { try { observe(this, JSON.parse(event.data)); } catch {} });
      this.addEventListener('close', cancel);
    }
    if (pending && pending.sent === null) {
      try { const data = JSON.parse(payload); if (data.t === 'drive' && data.action === pending.action) pending.sent = performance.now(); } catch {}
    }
    return original.call(this, payload);
  };
  window.addEventListener('pointerdown', event => {
    const button = event.target.closest?.('[data-action]');
    if (!button || button.disabled) return;
    cancel();
    if (!last || last.mode !== 'manual' || last.left || last.right || !last.fpga?.connected) return;
    const now = performance.now(), start = event.timeStamp;
    if (!Number.isFinite(start) || start > now || now - start > 1000) return;
    const action = button.dataset.action, duty = Math.round(Number(document.getElementById('speed').value) * 1350 / 100);
    if (!duty) return;
    pending = { action, start, sent: null, generation: last.generation, seq: last.fpga.applied_seq,
      spi: last.diag?.spi_ok ?? 0, left: signs[action][0] * duty, right: signs[action][1] * duty };
  }, true);
  window.addEventListener('pointercancel', cancel);
  window.addEventListener('blur', cancel);
  document.addEventListener('visibilitychange', () => { if (document.hidden) cancel(); });
  render();
})();
