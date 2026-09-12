(function () {
  'use strict';
  const dialog = document.getElementById('customer-celebration');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const form = document.getElementById('celebration-form');
  const shown = new Set();
  let current = null, busy = false, previousFocus = null;
  async function poll() {
    if (document.hidden || dialog.open || busy) return;
    busy = true;
    try {
      const response = await fetch(dialog.dataset.feed, {credentials:'same-origin', cache:'no-store', signal:AbortSignal.timeout(10000)});
      if (!response.ok) return;
      const data = await response.json();
      const item = data.notifications.find(n => !shown.has(n.id));
      if (!item || document.hidden) return;
      current = item; shown.add(item.id); previousFocus = document.activeElement;
      document.getElementById('celebration-title').textContent = item.title;
      document.getElementById('celebration-message').textContent = item.message;
      document.getElementById('celebration-error').hidden = true;
      const confetti = dialog.querySelector('.celebration-confetti'); confetti.replaceChildren();
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
        for (let i=0;i<22;i++) {
          const piece = document.createElement('i');
          piece.style.setProperty('--x', `${Math.random()*100}%`);
          piece.style.setProperty('--delay', `${Math.random()*.4}s`);
          piece.style.setProperty('--color', ['#2458dc','#20a874','#f5b83d','#d563a1'][i%4]);
          confetti.append(piece);
        }
      }
      dialog.showModal();
    } catch (_) { /* Retry at the next bounded poll; never disrupt checkout. */ }
    finally { busy = false; }
  }
  async function dismiss() {
    if (busy || !current) return;
    busy = true;
    try {
      const response = await fetch(`${dialog.dataset.feed}${current.id}/da-xem/`, {method:'POST',credentials:'same-origin',signal:AbortSignal.timeout(10000),headers:{'X-CSRFToken':form.querySelector('[name=csrfmiddlewaretoken]').value}});
      if (!response.ok) throw new Error('ack_failed');
      dialog.close(); current = null;
      if (previousFocus?.isConnected) previousFocus.focus();
    } catch (_) { document.getElementById('celebration-error').hidden = false; }
    finally { busy = false; }
  }
  form.addEventListener('submit', event => { event.preventDefault(); dismiss(); });
  function closeLocally() {
    dismiss(); dialog.close();
    if (previousFocus?.isConnected) previousFocus.focus();
  }
  document.getElementById('celebration-close').addEventListener('click', closeLocally);
  dialog.addEventListener('cancel', event => { event.preventDefault(); closeLocally(); });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
  setInterval(poll, 30000); poll();
})();
