const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const template = fs.readFileSync(path.join(__dirname, '../templates/public/checkout.html'), 'utf8');
const source = [...template.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(script => script.includes('function setDeliveryMethod'));

function harness() {
  const nodes = new Map();
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, {value: '', textContent: '', hidden: false,
      disabled: false, style: {}, attributes: {}, listeners: {}, classes: new Set(),
      setAttribute(name, value) { this.attributes[name] = value; },
      removeAttribute(name) { delete this.attributes[name]; },
      addEventListener(name, fn) { this.listeners[name] = fn; },
      classList: {add() {}, remove() {}}});
    return nodes.get(id);
  };
  const radios = [{value: 'HOME_DELIVERY', checked: true}, {value: 'STORE_PICKUP', checked: false}];
  const calls = [], timers = new Map();
  let timerId = 0, gps;
  const context = {console, AbortController, URLSearchParams, encodeURIComponent,
    document: {getElementById: node,
      querySelector: () => radios.find(r => r.checked), querySelectorAll: () => radios},
    navigator: {geolocation: {getCurrentPosition(success, error) { gps = {success, error}; }}},
    setTimeout(fn) { timers.set(++timerId, fn); return timerId; },
    clearTimeout(id) { timers.delete(id); },
    fetch(url, options) { return new Promise((resolve, reject) => calls.push({url, options, resolve, reject})); }};
  vm.runInNewContext(source, context);
  return {context, node, radios, calls, timers, gps: () => gps};
}
const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
function reply(call, shipping, total) {
  call.resolve({ok: true, json: async () => ({shipping_fee: shipping, total_amount: total,
    formatted_shipping_fee: shipping ? shipping + '₫' : 'Miễn phí', formatted_total_amount: total + '₫'})});
}

test('pickup selection refreshes server totals and blocks submit while pending', async () => {
  const h = harness();
  h.context.setDeliveryMethod('STORE_PICKUP');
  assert.equal(h.calls.length, 1);
  assert.match(h.calls[0].url, /delivery_method=STORE_PICKUP/);
  assert.equal(h.node('btn-place-order').disabled, true);
  assert.equal(h.radios[1].checked, true);
  assert.equal(h.node('branch_id').attributes.required, 'required');
  assert.equal(h.node('address').attributes.required, undefined);
  reply(h.calls[0], 0, 95000); await flush();
  assert.equal(h.node('summary-shipping-fee').textContent, 'Miễn phí');
  assert.equal(h.node('summary-grand-total').textContent, '95000₫');
  assert.equal(h.node('btn-place-order').disabled, false);
  assert.equal(h.timers.size, 0);
});

test('delivery switch race cannot restore an old price summary', async () => {
  const h = harness();
  h.context.setDeliveryMethod('STORE_PICKUP');
  h.context.setDeliveryMethod('HOME_DELIVERY');
  assert.equal(h.calls.length, 2);
  assert.equal(h.calls[0].options.signal.aborted, true);
  reply(h.calls[1], 30000, 125000); await flush();
  reply(h.calls[0], 0, 95000); await flush();
  assert.equal(h.node('summary-grand-total').textContent, '125000₫');
  assert.equal(h.node('address').attributes.required, 'required');
});

test('failed/malformed price summary requires retry, never displays success', async () => {
  for (const malformed of [false, true]) {
    const h = harness(); h.context.setDeliveryMethod('STORE_PICKUP');
    if (malformed) h.calls[0].resolve({ok: true, json: async () => ({shipping_fee: -1, total_amount: NaN})});
    else h.calls[0].reject(Error('network'));
    await flush();
    assert.equal(h.node('btn-place-order').disabled, true);
    assert.equal(h.node('checkout-summary-retry').hidden, false);
    assert.match(h.node('checkout-summary-status').textContent, /chưa|Chưa/);
    h.node('checkout-summary-retry').listeners.click();
    reply(h.calls[1], 0, 95000); await flush();
    assert.equal(h.node('btn-place-order').disabled, false);
    assert.equal(h.node('checkout-summary-retry').hidden, true);
  }
});

test('initial home selection requires address without an unnecessary price request', () => {
  const h = harness();
  assert.equal(h.node('address').attributes.required, 'required');
  assert.equal(h.calls.length, 0);
});

test('checkout GPS rejects invalid or coarse positions and clears stale coordinates', () => {
  for (const coords of [null, {}, {latitude: NaN, longitude: 106, accuracy: 10},
    {latitude: 91, longitude: 106, accuracy: 10}, {latitude: 10, longitude: 181, accuracy: 10},
    {latitude: 10, longitude: 106, accuracy: null}, {latitude: 10, longitude: 106, accuracy: 101}]) {
    const h = harness(); h.node('delivery-latitude').value = 'old';
    h.node('delivery-longitude').value = 'old';
    h.node('btn-use-delivery-location').listeners.click(); h.gps().success({coords});
    assert.equal(h.node('delivery-latitude').value, '');
    assert.equal(h.node('delivery-longitude').value, '');
    assert.match(h.node('delivery-location-status').textContent, /Không thể lấy vị trí chính xác/);
    assert.equal(h.node('btn-use-delivery-location').disabled, false);
  }
});

test('checkout GPS accepts reported accuracy boundary and handles denied/unavailable/timeout', () => {
  const h = harness(); h.node('btn-use-delivery-location').listeners.click();
  h.gps().success({coords: {latitude: 10, longitude: 106, accuracy: 100}});
  assert.equal(h.node('delivery-latitude').value, '10.000000');
  for (const code of [1, 2, 3]) {
    h.node('btn-use-delivery-location').listeners.click(); h.gps().error({code});
    assert.equal(h.node('delivery-latitude').value, '');
    assert.equal(h.node('delivery-longitude').value, '');
    assert.equal(h.node('btn-use-delivery-location').disabled, false);
    assert.match(h.node('delivery-location-status').textContent, /địa chỉ/);
  }
});

test('switching to pickup ignores a GPS callback from a previous delivery attempt', () => {
  const h = harness(); h.node('btn-use-delivery-location').listeners.click();
  h.context.setDeliveryMethod('STORE_PICKUP');
  h.gps().success({coords: {latitude: 10, longitude: 106, accuracy: 10}});
  assert.equal(h.node('delivery-latitude').value, '');
  assert.equal(h.node('btn-use-delivery-location').disabled, false);
  assert.doesNotMatch(h.node('delivery-location-status').textContent, /Đã nhận vị trí/);
});
