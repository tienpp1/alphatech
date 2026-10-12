// Execute actual branchfinder callbacks; never contact a map/routing provider.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require.resolve('../static/public/js/branch-finder.js'), 'utf8');

function browser() {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      textContent: id === 'bf-data' ? '[]' : '', value: '1', checked: false,
      disabled: false, hidden: true, listeners: {}, classList: {toggle() {}},
      replaceChildren() {}, setAttribute() {}, append() {},
      addEventListener(type, callback) { this.listeners[type] = callback; },
    });
    return elements.get(id);
  };
  const events = {};
  const map = {setView() { return this; }, removeLayer() {},
    on(type, callback) { events[type] = callback; return this; }};
  let callbacks, markers = 0, requests = 0;
  const context = {console, URLSearchParams, AbortController,
    document: {getElementById: element, querySelectorAll: () => [],
      createElement: tag => ({tagName: tag, textContent: ''})},
    window: {isSecureContext: true},
    navigator: {geolocation: {getCurrentPosition(success, error, options) {
      callbacks = {success, error, options};
    }}},
    L: {map: () => map, divIcon: options => options,
      marker: () => { markers++; return {bindPopup() { return this; },
        addTo() { return this; }, on() { return this; }}; },
      tileLayer: () => ({on() { return this; }, addTo() { return this; }})},
    fetch: () => { requests++; throw Error('no provider request is permitted'); },
  };
  vm.runInNewContext(source, context);
  return {
    element, get callbacks() { return callbacks; },
    get markers() { return markers; }, get requests() { return requests; },
    locate() { element('bf-locate').listeners.click(); },
    pick(lat, lng) {
      element('bf-pick').listeners.click();
      events.click({latlng: {lat, lng}});
    },
  };
}

test('GPS denied, unavailable and timeout re-enable controls without inventing a location', () => {
  for (const [code, message] of [[1, /chưa cho phép/], [2, /chưa xác định/], [3, /quá thời gian/]]) {
    const app = browser();
    app.locate();
    assert.equal(app.element('bf-locate').disabled, true);
    assert.equal(app.callbacks.options.maximumAge, 0);
    app.callbacks.error({code});
    assert.equal(app.element('bf-locate').disabled, false);
    assert.equal(app.element('bf-origin').textContent, '');
    assert.match(app.element('bf-status').textContent, message);
    assert.match(app.element('bf-status').textContent, /nhập địa chỉ hoặc chọn điểm/);
    assert.equal(app.markers, 0);
    assert.equal(app.requests, 0);
  }
});

test('failed or inaccurate GPS does not replace a manually confirmed origin', () => {
  for (const result of [{code: 1}, {coords: {latitude: 11, longitude: 107, accuracy: 500}}]) {
    const app = browser();
    app.pick(10, 106);
    const origin = app.element('bf-origin').textContent;
    assert.match(origin, /10\.00000, 106\.00000/);
    app.locate();
    if (result.code) app.callbacks.error(result);
    else app.callbacks.success(result);
    assert.equal(app.element('bf-origin').textContent, origin);
    assert.equal(app.element('bf-locate').disabled, false);
    assert.equal(app.markers, 1);
    assert.equal(app.requests, 0);
  }
});

test('late GPS success cannot overwrite a newer explicit map choice', () => {
  const app = browser();
  app.locate();
  const oldCallbacks = app.callbacks;
  app.pick(10, 106);
  const origin = app.element('bf-origin').textContent;
  oldCallbacks.success({coords: {latitude: 11, longitude: 107, accuracy: 10}});
  assert.equal(app.element('bf-origin').textContent, origin);
  assert.equal(app.element('bf-locate').disabled, false);
  assert.equal(app.markers, 1);
  assert.equal(app.requests, 0);
});
