/* Refresh only the bulletin feed, never the page or an editor's draft. */
(function () {
    'use strict';
    const feed = document.getElementById('bulletinLiveFeed');
    if (!feed) return;
    const status = document.getElementById('bulletinConnectionStatus');
    const workspace = feed.dataset.workspaceId;
    let busy = false, stopped = false, signature = null, timer;
    function element(tag, cls, text) {
        const node = document.createElement(tag);
        node.className = cls;
        node.textContent = text || '';
        return node;
    }
    function render(items) {
        const list = element('div', 'bulletin-live-list');
        list.style.cssText = 'display:flex; flex-direction:column; gap:16px; margin-bottom:3rem';
        if (!items.length) list.appendChild(element('p', 'bulletin-body-text', 'Chưa có bản tin phù hợp trong không gian làm việc này.'));
        items.forEach(item => {
            const card = element('article', 'bulletin-card' + (item.is_pinned ? ' is-pinned' : item.priority === 'URGENT' ? ' is-urgent' : ''));
            card.dataset.bulletinId = item.id;
            const kind = item.is_pinned ? 'pinned' : item.priority === 'URGENT' ? 'urgent' : 'normal';
            const badge = element('span', 'priority-badge ' + kind, item.priority_label);
            card.appendChild(badge);
            const heading = element('h2', '', item.title);
            heading.style.cssText = 'font-size:1.3rem; color:#f8fafc; margin:0; line-height:1.35';
            card.appendChild(heading);
            card.appendChild(element('div', 'bulletin-body-text', item.content));
            const meta = element('div', 'bulletin-meta-bar');
            meta.appendChild(element('span', '', 'Ban hành bởi: ' + item.author_name));
            meta.appendChild(element('span', '', new Date(item.created_at).toLocaleString('vi-VN')));
            if (feed.dataset.canManage === 'true') {
                const edit = element('a', 'btn btn-secondary', 'Sửa bản tin');
                edit.href = '/noibo/bang-tin/' + Number(item.id) + '/sua/?workspace_id=' + encodeURIComponent(workspace);
                meta.appendChild(edit);
            }
            card.appendChild(meta);
            list.appendChild(card);
        });
        feed.replaceChildren(list);
    }
    async function poll() {
        if (busy || stopped || document.hidden) return;
        busy = true;
        clearTimeout(timer);
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000);
        try {
            const response = await fetch('/api/v1/notifications/bulletins/?workspace_id=' + encodeURIComponent(workspace) + '&priority=' + encodeURIComponent(feed.dataset.priority || ''), {cache:'no-store', credentials:'same-origin', signal:controller.signal});
            if (response.status === 401 || response.status === 403 || response.redirected) {
                stopped = true;
                status.textContent = 'Phiên đăng nhập hoặc quyền truy cập đã thay đổi. Vui lòng đăng nhập lại.';
                return;
            }
            if (!response.ok) throw new Error('request');
            const data = await response.json();
            if (data.status !== 'success' || data.workspace_id !== workspace || !Array.isArray(data.bulletins)) throw new Error('response');
            // Ignore time_ago: it changes even when content is unchanged.
            const next = JSON.stringify(data.bulletins.map(item => [item.id,item.title,item.content,item.priority,item.is_pinned,item.author_name,item.created_at]));
            if (next !== signature) { render(data.bulletins); signature = next; }
            const count = document.getElementById('bulletinLiveCount');
            if (count) count.textContent = data.total_count;
            status.textContent = 'Đã kết nối · Bản tin cập nhật tự động mỗi 10 giây';
        } catch (error) {
            status.textContent = 'Chưa cập nhật được. Giữ nguyên bản tin đang xem và tự thử lại.';
        } finally {
            clearTimeout(timeout);
            busy = false;
            if (!stopped) timer = setTimeout(poll, 10000);
        }
    }
    document.addEventListener('visibilitychange', function () { if (!document.hidden) poll(); });
    window.addEventListener('online', poll);
    poll();
})();
