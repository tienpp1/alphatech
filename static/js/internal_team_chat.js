/* Workspace chat: bounded polling; no automatic replay of a failed POST. */
(function () {
    'use strict';
    const stream = document.getElementById('chatMessagesStream');
    if (!stream) return;
    const form = document.getElementById('chatForm');
    const input = document.getElementById('chatInputMessage');
    const button = document.getElementById('btnSendChat');
    const connection = document.getElementById('chatConnectionStatus');
    const sendStatus = document.getElementById('chatSendStatus');
    const workspace = stream.dataset.workspaceId;
    let cursor = Number(stream.dataset.latestId || 0);
    let polling = false, sending = false, stopped = false, timer;

    async function request(url, options) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000);
        try {
            const response = await fetch(url, Object.assign({cache: 'no-store', credentials: 'same-origin'}, options, {signal: controller.signal}));
            if (response.status === 401 || response.status === 403 || response.redirected) {
                stopped = true;
                button.disabled = true;
                connection.textContent = 'Phiên đăng nhập hoặc quyền truy cập đã thay đổi. Vui lòng đăng nhập lại.';
                throw new Error('access');
            }
            if (!response.ok) throw new Error('request');
            const data = await response.json();
            if (!(data.ok || data.status === 'success')) throw new Error('response');
            return data;
        } finally { clearTimeout(timeout); }
    }

    function append(item) {
        if (!Number.isSafeInteger(item.id) || item.id <= 0) return;
        if (stream.querySelector('[data-msg-id="' + item.id + '"]')) return;
        const atBottom = stream.scrollHeight - stream.scrollTop - stream.clientHeight < 100;
        const empty = document.getElementById('noMsgNotice');
        if (empty) empty.hidden = true;
        const row = document.createElement('div');
        row.className = 'chat-bubble-row ' + (item.is_me ? 'mine' : 'theirs');
        row.dataset.msgId = item.id;
        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.textContent = (item.sender_name || 'NV').slice(0, 2).toUpperCase();
        const content = document.createElement('div');
        content.className = 'chat-bubble-content';
        [['span', 'chat-sender-name', item.sender_name], ['div', 'chat-bubble-box', item.message], ['span', 'chat-time-stamp', item.created_at]].forEach(([tag, cls, text]) => {
            const child = document.createElement(tag);
            child.className = cls;
            child.textContent = text || '';
            content.appendChild(child);
        });
        row.appendChild(avatar);
        row.appendChild(content);
        const next = Array.from(stream.querySelectorAll('[data-msg-id]')).find(el => Number(el.dataset.msgId) > item.id);
        stream.insertBefore(row, next || null);
        // Sending a newer ID must not advance the read cursor past unseen peers.
        if (atBottom) stream.scrollTop = stream.scrollHeight;
    }

    async function poll() {
        if (polling || stopped || document.hidden) return;
        polling = true;
        clearTimeout(timer);
        let delay = 3000;
        try {
            const data = await request('/api/v1/notifications/chat/messages/?workspace_id=' + encodeURIComponent(workspace) + '&since_id=' + cursor);
            if (data.workspace_id !== workspace || !Array.isArray(data.messages)) throw new Error('workspace');
            data.messages.forEach(append);
            data.messages.forEach(item => { if (Number.isSafeInteger(item.id)) cursor = Math.max(cursor, item.id); });
            connection.textContent = 'Đã kết nối · Tin nhắn cập nhật tự động mỗi 3 giây';
            if (data.messages.length === 50) delay = 100; // Drain backlog without skipping pages.
        } catch (error) {
            if (!stopped) connection.textContent = 'Chưa kết nối được. Hệ thống sẽ thử lại; nội dung chưa gửi được giữ nguyên.';
            delay = 10000;
        } finally {
            polling = false;
            if (!stopped) timer = setTimeout(poll, delay);
        }
    }

    form.addEventListener('submit', async function (event) {
        event.preventDefault();
        const text = input.value.trim();
        if (!text || sending || stopped) return;
        sending = true;
        button.disabled = true;
        sendStatus.textContent = 'Đang gửi…';
        try {
            const data = await request('/api/v1/notifications/chat/send/', {
                method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value},
                body: JSON.stringify({workspace_id: workspace, message: text})
            });
            const id = data.message_id;
            if (!Number.isSafeInteger(id)) throw new Error('response');
            append({id: id, is_me: true, sender_name: data.sender_name || 'Bạn', message: data.message.text, created_at: data.created_at});
            if (input.value.trim() === text) input.value = '';
            sendStatus.textContent = 'Đã gửi tin nhắn.';
            poll();
        } catch (error) {
            sendStatus.textContent = 'Chưa xác nhận được tin đã gửi. Nội dung được giữ lại; hãy kiểm tra kênh trước khi gửi lại để tránh trùng.';
        } finally {
            sending = false;
            button.disabled = stopped;
        }
    });
    document.addEventListener('visibilitychange', function () { if (!document.hidden) poll(); });
    window.addEventListener('online', poll);
    window.addEventListener('offline', function () { connection.textContent = 'Thiết bị đang mất mạng. Nội dung chưa gửi được giữ nguyên.'; });
    stream.scrollTop = stream.scrollHeight;
    poll();
})();
