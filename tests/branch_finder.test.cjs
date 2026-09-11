const test = require('node:test');
const assert = require('node:assert/strict');
const {validPoint, distanceKm, inRadius, googleURL, shortestReturned} = require('../static/public/js/branch-finder.js');
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
