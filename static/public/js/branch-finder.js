/* Public directory only. No location persistence, automatic GPS, or fabricated routes. */
(function () {
  'use strict';
  const validPoint = p => p && Number.isFinite(p.lat) && Number.isFinite(p.lng) && Math.abs(p.lat) <= 90 && Math.abs(p.lng) <= 180;
  function distanceKm(a, b) {
    const rad = n => n * Math.PI / 180;
    const h = Math.sin(rad(b.lat - a.lat) / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(rad(b.lng - a.lng) / 2) ** 2;
    return 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, h)));
  }
  const inRadius = (branches, center, km) => branches.filter(b => validPoint(b) && distanceKm(center, b) <= km);
  const googleURL = (origin, destination) => 'https://www.google.com/maps/dir/?' + new URLSearchParams({api: '1', origin: `${origin.lat},${origin.lng}`, destination: `${destination.lat},${destination.lng}`, travelmode: 'driving'});
  const shortestReturned = routes => (Array.isArray(routes) ? routes : []).filter(r => r && Number.isFinite(r.distance) && r.distance >= 0 && Number.isFinite(r.duration) && r.duration >= 0 && r.geometry?.type === 'LineString' && Array.isArray(r.geometry.coordinates) && r.geometry.coordinates.length >= 2 && r.geometry.coordinates.every(c => Array.isArray(c) && validPoint({lat: c[1], lng: c[0]}))).sort((a, b) => a.distance - b.distance)[0];
  if (typeof module !== 'undefined' && module.exports) module.exports = {validPoint, distanceKm, inRadius, googleURL, shortestReturned};
  if (typeof document === 'undefined') return;
  const $ = id => document.getElementById(id);
  if (!$('bf-map')) return;
  const status = message => { $('bf-status').textContent = message; };
  if (typeof L === 'undefined') { status('Không tải được thư viện bản đồ. Hãy tải lại trang hoặc dùng địa chỉ Google Maps bên dưới.'); return; }
  const all = JSON.parse($('bf-data').textContent), branches = all.filter(validPoint);
  const markers = new Map();
  let origin = null, userMarker, accuracyCircle, radiusCenter, radiusCircle, routeLayer;
  let picking = false, version = 0, searchVersion = 0, locatingVersion = 0;
  let routingController, searchingController;
  const map = L.map('bf-map', {scrollWheelZoom: false}).setView([10.7769, 106.7009], 12);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, referrerPolicy: 'origin', attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).on('tileerror', () => { $('bf-tile-error').hidden = false; }).addTo(map);
  const fit = points => { if (points.length) map.fitBounds(points.map(p => [p.lat, p.lng]), {padding: [36, 36], maxZoom: 15, animate: false}); };
  const node = (tag, text) => { const element = document.createElement(tag); element.textContent = text; return element; };
  const card = b => $('branch-card-' + b.id);
  const kmText = meters => (meters / 1000).toLocaleString('vi-VN', {maximumFractionDigits: 1}) + ' km';
  function cancelRouting() {
    version++;
    if (routingController) routingController.abort();
    if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null; }
    $('bf-route').hidden = true;
    $('bf-nearest').disabled = !origin || !branches.length;
  }
  function select(b) {
    all.forEach(item => card(item).classList.toggle('bf-selected', item.id === b.id));
  }
  function refreshRadius() {
    const active = $('bf-radius-mode').checked && radiusCenter;
    const km = Number($('bf-radius').value);
    $('bf-radius-value').textContent = km + ' km';
    if (radiusCircle) { map.removeLayer(radiusCircle); radiusCircle = null; }
    const visible = active ? inRadius(branches, radiusCenter, km) : all;
    const ids = new Set(visible.map(b => b.id));
    all.forEach(b => {
      card(b).hidden = !ids.has(b.id);
      const marker = markers.get(b.id);
      if (marker) { if (ids.has(b.id)) marker.addTo(map); else map.removeLayer(marker); }
      card(b).querySelector('.bf-distance').textContent = !validPoint(b) ? 'Chưa có tọa độ; vui lòng xem địa chỉ hoặc gọi cửa hàng.' : active && ids.has(b.id) ? distanceKm(radiusCenter, b).toLocaleString('vi-VN', {maximumFractionDigits: 2}) + ' km từ tâm (đường chim bay)' : '';
    });
    if (active) radiusCircle = L.circle([radiusCenter.lat, radiusCenter.lng], {radius: km * 1000, color: '#7c3aed', fillOpacity: .08, interactive: false}).addTo(map);
    $('bf-count').textContent = active ? `${visible.length}/${all.length} chi nhánh trong ${km} km` : `${all.length} chi nhánh · ${branches.length} có tọa độ`;
    $('bf-empty').hidden = !active || visible.length > 0;
    $('bf-radius-origin').disabled = !origin || !$('bf-radius-mode').checked;
  }
  function setOrigin(point, label, accuracy) {
    if (!validPoint(point)) { status('Vị trí không hợp lệ. Vui lòng chọn lại.'); return; }
    cancelRouting(); locatingVersion++; searchVersion++;
    if (searchingController) searchingController.abort();
    origin = {lat: point.lat, lng: point.lng};
    if (userMarker) map.removeLayer(userMarker);
    if (accuracyCircle) map.removeLayer(accuracyCircle);
    userMarker = L.marker([origin.lat, origin.lng], {icon: L.divIcon({className: 'bf-marker bf-marker-user', html: '●', iconSize: [24, 24]}), title: 'Điểm xuất phát của bạn'}).bindPopup(node('span', label)).addTo(map);
    if (Number.isFinite(accuracy) && accuracy > 0) accuracyCircle = L.circle([origin.lat, origin.lng], {radius: accuracy, color: '#087c56', fillOpacity: .06, interactive: false}).addTo(map);
    $('bf-origin').textContent = `${label} (${origin.lat.toFixed(5)}, ${origin.lng.toFixed(5)})` + (accuracy ? ` · Sai số khoảng ${Math.round(accuracy)} m` : '');
    $('bf-nearest').disabled = !branches.length;
    document.querySelectorAll('[data-route]').forEach(button => { button.disabled = !branches.some(b => String(b.id) === button.dataset.route); });
    $('bf-locate').disabled = false; $('bf-search-button').disabled = false;
    $('bf-search-results').replaceChildren();
    map.setView([origin.lat, origin.lng], 14, {animate: false});
    refreshRadius(); status('Đã chọn điểm xuất phát. Bạn có thể tìm cửa hàng gần nhất hoặc bấm Dẫn đường tại chi nhánh muốn đến.');
  }
  async function fetchJSON(url, controller) {
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, {signal: controller.signal, credentials: 'omit'});
      if (!response.ok) throw new Error('provider_unavailable');
      return await response.json();
    } finally { clearTimeout(timeout); }
  }
  async function directions(b) {
    if (!origin || !validPoint(b)) { status('Hãy chọn điểm xuất phát và chi nhánh có tọa độ trước khi dẫn đường.'); return; }
    cancelRouting(); select(b);
    const current = version, start = {...origin};
    routingController = new AbortController();
    $('bf-route').hidden = false;
    $('bf-route-title').textContent = 'Đường đến ' + b.name;
    $('bf-google-route').href = googleURL(start, b);
    $('bf-route-summary').textContent = 'Đang tìm tuyến đường ô tô…';
    status('Đang tải tuyến đường thật. Bạn cũng có thể mở Google Maps.');
    try {
      const data = await fetchJSON(`https://router.project-osrm.org/route/v1/driving/${start.lng},${start.lat};${b.lng},${b.lat}?alternatives=true&overview=full&geometries=geojson`, routingController);
      if (current !== version) return;
      const route = data.code === 'Ok' && shortestReturned(data.routes);
      if (!route) throw new Error('no_route');
      routeLayer = L.geoJSON(route.geometry, {style: {color: '#2458dc', weight: 6, opacity: .85}}).addTo(map);
      map.fitBounds(routeLayer.getBounds(), {padding: [36, 36], animate: false});
      $('bf-route-summary').textContent = `${kmText(route.distance)} · Khoảng ${Math.max(1, Math.round(route.duration / 60))} phút bằng ô tô (ước tính).`;
      status('Đã hiển thị tuyến đường ô tô tham khảo tới ' + b.name + '.');
    } catch (_) {
      if (current !== version) return;
      $('bf-route-summary').textContent = 'Chưa lấy được tuyến đường. Hãy thử lại hoặc mở Google Maps bên dưới.';
      status('Dịch vụ định tuyến không phản hồi hoặc không tìm thấy đường. Không hiển thị đường thẳng thay cho đường đi.');
    }
  }
  branches.forEach((b, i) => {
    const popup = document.createElement('div');
    popup.append(node('strong', b.name), node('p', b.address));
    const button = node('button', 'Dẫn đường tới đây'); button.type = 'button'; button.addEventListener('click', () => directions(b)); popup.append(button);
    const marker = L.marker([b.lat, b.lng], {icon: L.divIcon({className: 'bf-marker', html: String(i + 1), iconSize: [32, 32]}), title: b.name}).bindPopup(popup).addTo(map);
    marker.on('click', () => { cancelRouting(); select(b); }); markers.set(b.id, marker);
    card(b).querySelector('[data-focus]').disabled = false;
  });
  all.filter(b => !validPoint(b)).forEach(b => { card(b).querySelector('.bf-distance').textContent = 'Chưa có tọa độ; vui lòng xem địa chỉ hoặc gọi cửa hàng.'; });
  fit(branches);
  document.querySelectorAll('[data-focus]').forEach(button => button.addEventListener('click', () => {
    const b = branches.find(item => String(item.id) === button.dataset.focus);
    if (!b) return;
    cancelRouting(); select(b); map.setView([b.lat, b.lng], 16, {animate: false}); markers.get(b.id).openPopup();
    $('bf-map').scrollIntoView({block: 'center', behavior: 'instant'});
  }));
  document.querySelectorAll('[data-route]').forEach(button => button.addEventListener('click', () => directions(branches.find(b => String(b.id) === button.dataset.route))));
  $('bf-locate').addEventListener('click', () => {
    if (!navigator.geolocation || !window.isSecureContext) { status('Lấy vị trí cần HTTPS và trình duyệt hỗ trợ. Hãy nhập địa chỉ hoặc chọn điểm trên bản đồ.'); return; }
    const current = ++locatingVersion;
    $('bf-locate').disabled = true; status('Đang xin quyền lấy vị trí. Hãy cho phép trong thông báo của trình duyệt.');
    navigator.geolocation.getCurrentPosition(position => {
      if (current !== locatingVersion) return;
      setOrigin({lat: position.coords.latitude, lng: position.coords.longitude}, 'Vị trí thiết bị', position.coords.accuracy);
    }, error => {
      if (current !== locatingVersion) return;
      $('bf-locate').disabled = false;
      status(({1: 'Bạn chưa cho phép truy cập vị trí.', 2: 'Thiết bị chưa xác định được vị trí.', 3: 'Lấy vị trí quá thời gian chờ.'}[error.code] || 'Không lấy được vị trí.') + ' Hãy nhập địa chỉ hoặc chọn điểm trên bản đồ.');
    }, {enableHighAccuracy: true, timeout: 12000, maximumAge: 0});
  });
  function updateMode() {
    $('bf-pick').setAttribute('aria-pressed', String(picking));
    $('bf-map').classList.toggle('bf-picking', picking || $('bf-radius-mode').checked);
    $('bf-radius').disabled = !$('bf-radius-mode').checked;
    refreshRadius();
  }
  $('bf-pick').addEventListener('click', () => { picking = !picking; $('bf-radius-mode').checked = false; updateMode(); status(picking ? 'Bấm một điểm trên bản đồ làm điểm xuất phát. Hoặc nhập địa chỉ ở ô tìm kiếm.' : 'Đã tắt chế độ chọn vị trí.'); });
  map.on('click', event => {
    const point = {lat: event.latlng.lat, lng: event.latlng.lng};
    if ($('bf-radius-mode').checked) { cancelRouting(); radiusCenter = point; refreshRadius(); status('Đã cập nhật tâm tìm kiếm. Danh sách bên dưới chỉ hiện chi nhánh trong vòng tròn.'); }
    else if (picking) { setOrigin(point, 'Vị trí bạn chọn'); picking = false; updateMode(); }
  });
  $('bf-radius-mode').addEventListener('change', () => { cancelRouting(); picking = false; updateMode(); status($('bf-radius-mode').checked ? 'Bấm bản đồ để chọn tâm hoặc dùng nút Lấy điểm xuất phát làm tâm.' : 'Đã tắt lọc bán kính.'); });
  $('bf-radius').addEventListener('input', refreshRadius);
  $('bf-radius-origin').addEventListener('click', () => { if (origin) { radiusCenter = {...origin}; refreshRadius(); map.fitBounds(radiusCircle.getBounds(), {animate: false}); status('Đang tìm quanh điểm xuất phát của bạn.'); } });
  $('bf-reset').addEventListener('click', () => { $('bf-radius-mode').checked = false; picking = false; cancelRouting(); updateMode(); fit(branches); status('Đang hiển thị tất cả chi nhánh. Điểm xuất phát của bạn được giữ nguyên.'); });
  $('bf-nearest').addEventListener('click', async () => {
    if (!origin || !branches.length) return;
    cancelRouting(); const current = version; routingController = new AbortController();
    $('bf-nearest').disabled = true; status('Đang so sánh quãng đường ô tô tới các chi nhánh…');
    try {
      const coordinates = [origin, ...branches].map(p => `${p.lng},${p.lat}`).join(';');
      const data = await fetchJSON(`https://router.project-osrm.org/table/v1/driving/${coordinates}?sources=0&annotations=distance`, routingController);
      if (current !== version) return;
      if (data.code !== 'Ok' || !Array.isArray(data.distances?.[0])) throw new Error('no_table');
      const ranked = branches.map((b, i) => ({b, meters: data.distances[0][i + 1]})).filter(row => Number.isFinite(row.meters) && row.meters >= 0).sort((a, b) => a.meters - b.meters);
      if (!ranked.length) throw new Error('no_route');
      $('bf-radius-mode').checked = false; picking = false; updateMode();
      const nearest = ranked[0]; select(nearest.b); fit([origin, nearest.b]); markers.get(nearest.b.id).openPopup();
      ranked.forEach(row => { card(row.b).querySelector('.bf-distance').textContent = kmText(row.meters) + ' theo tuyến ô tô được cung cấp'; });
      status(`Gần nhất theo quãng đường ô tô được cung cấp: ${nearest.b.name} (${kmText(nearest.meters)}). Bấm Dẫn đường tại chi nhánh này.` + (ranked.length < branches.length ? ` Chỉ ${ranked.length}/${branches.length} chi nhánh có tuyến; chưa so sánh được tất cả.` : ''));
    } catch (_) { if (current === version) status('Chưa so sánh được đường đi. Hãy thử lại hoặc chọn chi nhánh và mở Google Maps; không dùng đường chim bay để giả kết quả đường bộ.'); }
    finally { if (current === version) $('bf-nearest').disabled = false; }
  });
  $('bf-search').addEventListener('submit', async event => {
    event.preventDefault(); const query = $('bf-address').value.trim(); if (query.length < 3) return;
    if (searchingController) searchingController.abort();
    searchingController = new AbortController(); const current = ++searchVersion;
    $('bf-search-button').disabled = true; $('bf-search-results').replaceChildren(); status('Đang tìm địa chỉ…');
    try {
      const center = map.getCenter();
      const data = await fetchJSON('https://photon.komoot.io/api/?' + new URLSearchParams({q: query, limit: '5', lat: center.lat, lon: center.lng}), searchingController);
      if (current !== searchVersion) return;
      const results = (data.features || []).filter(f => f.geometry?.type === 'Point' && validPoint({lat: f.geometry.coordinates[1], lng: f.geometry.coordinates[0]}));
      results.forEach(feature => {
        const p = feature.properties || {}, c = feature.geometry.coordinates;
        const label = [...new Set([p.name, [p.housenumber, p.street].filter(Boolean).join(' '), p.district, p.city, p.state, p.country].filter(Boolean))].join(', ') || `${c[1]}, ${c[0]}`;
        const button = node('button', label); button.type = 'button'; button.className = 'bf-search-result';
        button.addEventListener('click', () => setOrigin({lat: c[1], lng: c[0]}, label)); $('bf-search-results').append(button);
      });
      status(results.length ? 'Chọn địa chỉ đúng trong các kết quả bên dưới ô tìm kiếm.' : 'Chưa tìm thấy địa chỉ. Thử thêm quận, thành phố hoặc chọn trực tiếp trên bản đồ.');
    } catch (_) { if (current === searchVersion) status('Không kết nối được dịch vụ tìm địa chỉ. Hãy thử lại hoặc dùng Lấy vị trí / Chọn vị trí trên bản đồ.'); }
    finally { if (current === searchVersion) $('bf-search-button').disabled = false; }
  });
  refreshRadius();
})();
