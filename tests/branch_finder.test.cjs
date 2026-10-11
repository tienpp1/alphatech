const test = require('node:test');
const assert = require('node:assert/strict');
const {validPoint, distanceKm, inRadius, googleURL, shortestReturned, chooseRoute, accuracyMessage, acceptableDevicePosition, stepText} = require('../static/public/js/branch-finder.js');
test('coordinates: zero allowed, absent/non-finite/out-of-range rejected', () => {
  assert.ok(validPoint({lat:0,lng:0}));
  for (const p of [{lat:null,lng:1},{lat:NaN,lng:1},{lat:91,lng:1},{lat:1,lng:181},{lat:'10',lng:106}]) assert.ok(!validPoint(p));
});
test('Haversine uses kilometers and is symmetric', () => {
  const a={lat:0,lng:0},b={lat:0,lng:1};
  assert.equal(distanceKm(a,a),0);
  assert.ok(Math.abs(distanceKm(a,b)-111.195)<.01);
  assert.equal(distanceKm(a,b),distanceKm(b,a));
});
test('radius filters 1 to 10km and excludes missing coordinates', () => {
  const a={lat:0,lng:0}, b={lat:0,lng:.05}, c={lat:0,lng:.2};
  assert.deepEqual(inRadius([a,b,c,{lat:null,lng:null}],a,1),[a]);
  assert.deepEqual(inRadius([a,b,c],a,10),[a,b]);
});
test('antipodal and antimeridian distances remain finite', () => {
  assert.ok(Number.isFinite(distanceKm({lat:0,lng:0},{lat:0,lng:180})));
  assert.ok(distanceKm({lat:0,lng:179.99},{lat:0,lng:-179.99})<3);
});
test('Google directions preserves origin and selected destination', () => {
  const u=new URL(googleURL({lat:10,lng:106},{lat:11,lng:107}));
  assert.equal(u.hostname,'www.google.com');
  assert.equal(u.searchParams.get('origin'),'10,106');
  assert.equal(u.searchParams.get('destination'),'11,107');
});
test('shortest of provided road alternatives, not first/fastest', () => {
  const geometry={type:'LineString',coordinates:[[106,10],[107,11]]};
  const a={distance:200,duration:20,geometry},b={distance:100,duration:30,geometry};
  assert.equal(shortestReturned([a,b]),b);
});
test('missing or malformed routing data never produces a fake route', () => {
  assert.equal(shortestReturned([]),undefined);
  assert.equal(shortestReturned([{distance:100,duration:10}]),undefined);
  assert.equal(shortestReturned([null, {distance:1,duration:1,geometry:{type:'LineString'}}]),undefined);
  assert.equal(shortestReturned({}),undefined);
});
test('route preference distinguishes distance from duration', () => {
  const geometry={type:'LineString',coordinates:[[106,10],[107,11]]};
  const a={distance:200,duration:20,geometry},b={distance:100,duration:30,geometry};
  assert.equal(chooseRoute([a,b],'distance'),b);
  assert.equal(chooseRoute([a,b],'duration'),a);
  assert.equal(chooseRoute([],'duration'),undefined);
});
test('coarse or unknown GPS accuracy is never represented as precise', () => {
  assert.match(accuracyMessage(2500),/chỉ gần đúng/);
  assert.match(accuracyMessage(undefined),/chưa cung cấp sai số/);
  assert.match(accuracyMessage(20),/20 m/);
});
test('device coordinates are rejected before routing when accuracy is absent or exceeds 100m', () => {
  for (const accuracy of [undefined, null, -1, NaN, Infinity, 101, 2500]) {
    assert.equal(Boolean(acceptableDevicePosition({latitude: 10, longitude: 106, accuracy})), false);
  }
  assert.equal(acceptableDevicePosition({latitude: 10, longitude: 106, accuracy: 100}), true);
  assert.equal(acceptableDevicePosition({latitude: 10, longitude: 106, accuracy: 0}), true);
  assert.equal(acceptableDevicePosition({latitude: 91, longitude: 106, accuracy: 10}), false);
});
test('actual GPS callback never places a coarse/unknown origin or contacts a routing provider', () => {
  const fs = require('node:fs');
  const vm = require('node:vm');
  const source = fs.readFileSync(require.resolve('../static/public/js/branch-finder.js'), 'utf8');
  for (const accuracy of [undefined, 500, NaN]) {
    const elements = new Map();
    const element = id => {
      if (!elements.has(id)) elements.set(id, {textContent: id === 'bf-data' ? '[]' : '', value: '1', checked: false,
        disabled: false, hidden: true, listeners: {}, classList: {toggle() {}}, replaceChildren() {},
        setAttribute() {}, addEventListener(type, callback) { this.listeners[type] = callback; }});
      return elements.get(id);
    };
    const map = {setView() { return this; }, on() { return this; }};
    let markerCalls = 0, providerCalls = 0;
    const context = {console, URLSearchParams, AbortController,
      document: {getElementById: element, querySelectorAll: () => []},
      window: {isSecureContext: true},
      navigator: {geolocation: {getCurrentPosition(success) { success({coords: {latitude: 10, longitude: 106, accuracy}}); }}},
      L: {map: () => map, marker: () => { markerCalls++; throw Error('must not place inaccurate marker'); },
        tileLayer: () => ({on() { return this; }, addTo() { return this; }})},
      fetch: () => { providerCalls++; throw Error('must not route inaccurate position'); }};
    vm.runInNewContext(source, context);
    element('bf-locate').listeners.click();
    assert.equal(markerCalls, 0);
    assert.equal(providerCalls, 0);
    assert.equal(element('bf-origin').textContent, '');
    assert.equal(element('bf-locate').disabled, false);
    assert.match(element('bf-status').textContent, /Không thể lấy vị trí chính xác/);
  }
});
test('OSM steps are translated to Vietnamese without inventing a street', () => {
  assert.equal(stepText({maneuver:{type:'turn',modifier:'right'},name:'Nguyễn Huệ',distance:52}), 'Rẽ phải · Nguyễn Huệ · 52 m');
  assert.equal(stepText({maneuver:{type:'arrive'}}),'Đến điểm đích');
});
