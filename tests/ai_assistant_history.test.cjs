// Execute the actual assistant template script, not a duplicate implementation.
// Minimal DOM/fetch adapters keep these regressions offline and dependency-free.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const template = fs.readFileSync(path.join(__dirname, '../templates/ai/assistant.html'), 'utf8');
const script = [...template.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(source => source.includes('async function loadHistory'));
assert.ok(script, 'load the real assistant script from its template');
const escaped = value => String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');

class Element {
  constructor(id = '') {
    this.id = id; this.children = []; this.parentNode = null; this.attributes = new Map();
    this.listeners = new Map(); this.dataset = {}; this.style = {}; this.value = '';
    this.disabled = false; this.focused = false; this._html = ''; this._text = '';
    this.className = '';
    this.classList = {
      contains: name => this.className.split(/\s+/).includes(name),
      add: name => { if (!this.classList.contains(name)) this.className = `${this.className} ${name}`.trim(); },
      remove: name => { this.className = this.className.split(/\s+/).filter(value => value !== name).join(' '); },
      toggle: (name, enabled) => { if (enabled) this.classList.add(name); else this.classList.remove(name); },
    };
  }
  get innerHTML() { return this._html + this.children.map(child => child.innerHTML).join(''); }
  set innerHTML(value) { this.replaceChildren(); this._html = String(value); this._text = ''; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this.replaceChildren(); this._text = String(value ?? ''); this._html = escaped(value); }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  removeAttribute(name) { this.attributes.delete(name); }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
  replaceChildren(...children) {
    for (const child of this.children) child.parentNode = null;
    this.children = []; this._html = ''; this._text = '';
    for (const child of children) this.appendChild(child);
  }
  remove() {
    if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(child => child !== this);
    this.parentNode = null;
  }
  addEventListener(type, callback) { this.listeners.set(type, callback); }
  dispatchEvent(event) { return this.listeners.get(event.type)?.(event); }
  trigger(type, extra = {}) { return this.dispatchEvent({type, preventDefault() {}, ...extra}); }
  focus() { this.focused = true; }
  get scrollHeight() { return this.children.length; }
}

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}
function response(data, ok = true) { return {ok, async json() { return data; }}; }
function history(id, messages) { return response({success: true, data: {session_id: id, title: `Session ${id}`, messages}}); }
function setup(fetcher) {
  const ids = ['chat-messages', 'chat-form', 'chat-input', 'btn-send', 'btn-text', 'btn-spinner', 'citations-body', 'btn-new-chat'];
  const elements = Object.fromEntries(ids.map(id => [id, new Element(id)]));
  const sessions = [11, 22].map(id => { const node = new Element(); node.dataset.sessionId = String(id); return node; });
  const requests = []; const timers = new Map(); let timerId = 0; let ready;
  const document = {
    cookie: 'csrftoken=offline-test-csrf',
    addEventListener(type, callback) { assert.equal(type, 'DOMContentLoaded'); ready = callback; },
    getElementById(id) { assert.ok(elements[id], `unexpected element ${id}`); return elements[id]; },
    querySelectorAll(selector) { return selector === '.session-item' ? sessions : []; },
    createElement() { return new Element(); },
  };
  vm.runInNewContext(script.replace('{{ active_workspace.id|escapejs }}', 'offline-workspace'), {
    document, AbortController, Event,
    setTimeout(callback) { timers.set(++timerId, callback); return timerId; },
    clearTimeout(id) { timers.delete(id); },
    fetch(url, options) { requests.push({url, options}); return fetcher(url, options); },
  }, {filename: 'templates/ai/assistant.html'});
  ready();
  const send = async text => { elements['chat-input'].value = text; await elements['chat-form'].trigger('submit'); };
  return {elements, sessions, requests, timers, send};
}
const chatAnswer = id => response({success: true, data: {
  session_id: id, answer: 'Câu trả lời mới', sources: [], tools_used: [], generation_metadata: {mode: 'DETERMINISTIC'},
}});

test('history calls the real endpoint and normalizes USER/ASSISTANT without exposing SYSTEM', async () => {
  const pending = deferred(); const app = setup(() => pending.promise);
  const previous = new Element(); previous.textContent = 'Giữ nội dung trước khi tải';
  app.elements['chat-messages'].appendChild(previous);
  const loaded = app.sessions[0].trigger('click');
  assert.equal(app.requests[0].url, '/api/v1/ai/sessions/11/messages/');
  assert.equal(app.requests[0].options.headers['X-Workspace-ID'], 'offline-workspace');
  assert.equal(app.elements['chat-messages'].getAttribute('aria-busy'), 'true');
  assert.equal(app.elements['btn-send'].disabled, true);
  assert.equal(app.elements['chat-messages'].children[0], previous);
  pending.resolve(history(11, [
    {role: 'SYSTEM', content: 'Private grounding instruction'},
    {role: 'USER', content: 'Câu hỏi\nDòng thứ hai'},
    {role: 'ASSISTANT', content: 'Trả lời đã lưu'},
    {role: 'UNKNOWN', content: 'Never render this'},
  ]));
  await loaded;
  const rows = app.elements['chat-messages'].children;
  assert.deepEqual(rows.map(row => row.className), ['message-row user', 'message-row assistant']);
  assert.match(rows[0].innerHTML, /Câu hỏi<br>Dòng thứ hai/);
  assert.match(rows[1].innerHTML, /Trả lời đã lưu/);
  assert.doesNotMatch(app.elements['chat-messages'].innerHTML, /Private grounding|Never render/);
  assert.equal(app.sessions[0].getAttribute('aria-pressed'), 'true');
  assert.equal(app.sessions[1].getAttribute('aria-pressed'), 'false');
  assert.equal(app.elements['chat-messages'].getAttribute('aria-busy'), null);
  assert.equal(app.elements['btn-send'].disabled, false);
  assert.equal(app.timers.size, 0);
});

test('history restores citations/tools from the last assistant and safely escapes text', async () => {
  const app = setup(() => history(11, [
    {role: 'ASSISTANT', content: 'Earlier', sources: [{document_title: 'Old source', chunk_id: 1, similarity: .1}]},
    {role: 'USER', content: '<img src=x onerror=alert(1)>'},
    {role: 'ASSISTANT', content: '<script>alert(1)</script>',
      sources: [{document_title: '<b>Approved guide</b>', chunk_id: 9, page_number: 2, similarity: .875}],
      tools_used: [{tool: '<stock>', status: '<SUCCESS>'}]},
    {role: 'SYSTEM', content: 'Hidden'},
  ]));
  await app.sessions[0].trigger('click');
  assert.match(app.elements['citations-body'].innerHTML, /Đoạn trích #9 • Trang 2/);
  assert.match(app.elements['citations-body'].innerHTML, /Điểm truy xuất 88% · Không phải độ chính xác/);
  assert.match(app.elements['citations-body'].innerHTML, /&lt;b&gt;Approved guide&lt;\/b&gt;/);
  assert.match(app.elements['citations-body'].innerHTML, /&lt;stock&gt;\(\)/);
  assert.match(app.elements['citations-body'].innerHTML, /&lt;SUCCESS&gt;/);
  assert.doesNotMatch(app.elements['citations-body'].innerHTML, /Old source/);
  assert.match(app.elements['chat-messages'].innerHTML, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.doesNotMatch(app.elements['chat-messages'].innerHTML, /<script>|<img /);
});

test('new chat resets active history, citations and session ID sent to the server', async () => {
  const app = setup(url => url.includes('/messages/') ? history(11, [{role: 'ASSISTANT', content: 'Old session'}]) : chatAnswer(33));
  await app.sessions[0].trigger('click');
  app.elements['btn-new-chat'].trigger('click');
  assert.equal(app.sessions[0].classList.contains('active'), false);
  assert.equal(app.sessions[0].getAttribute('aria-pressed'), 'false');
  assert.match(app.elements['chat-messages'].innerHTML, /Bắt đầu cuộc trò chuyện mới/);
  assert.doesNotMatch(app.elements['chat-messages'].innerHTML, /Old session/);
  assert.match(app.elements['citations-body'].innerHTML, /Chưa có trích dẫn/);
  await app.send('New question');
  const posted = app.requests.at(-1);
  assert.equal(posted.url, '/api/v1/ai/chat/');
  assert.equal(JSON.parse(posted.options.body).session_id, null);
  assert.equal(posted.options.headers['X-CSRFToken'], 'offline-test-csrf');
  assert.equal(app.elements['chat-input'].focused, true);
});

test('failed history retains previous messages, citations, active selection and session ID', async () => {
  const app = setup(url => {
    if (url.includes('/11/')) return history(11, [{role: 'ASSISTANT', content: 'Previous successful history', sources: [{document_title: 'Kept source', chunk_id: 1, similarity: .9}]}]);
    if (url.includes('/22/')) return response({success: false, error: {code: 'NOT_FOUND'}}, false);
    return chatAnswer(11);
  });
  await app.sessions[0].trigger('click');
  const previous = app.elements['chat-messages'].children[0];
  const citations = app.elements['citations-body'].innerHTML;
  await app.sessions[1].trigger('click');
  assert.equal(app.elements['chat-messages'].children[0], previous);
  assert.match(app.elements['chat-messages'].textContent, /Chưa tải được hội thoại/);
  assert.equal(app.elements['citations-body'].innerHTML, citations);
  assert.equal(app.sessions[0].getAttribute('aria-pressed'), 'true');
  assert.equal(app.sessions[1].getAttribute('aria-pressed'), 'false');
  assert.equal(app.elements['btn-send'].disabled, false);
  await app.send('Continue previous session');
  assert.equal(JSON.parse(app.requests.at(-1).options.body).session_id, 11);
});

test('malformed history is rejected without clearing existing content', async () => {
  for (const invalid of [response({success: true, data: {messages: null}}), response({success: true, data: {messages: {}}}), response({success: false}), response(null), response('not a JSON object')]) {
    const app = setup(() => invalid);
    app.elements['chat-messages'].innerHTML = '<p>Existing content</p>';
    await app.sessions[0].trigger('click');
    assert.match(app.elements['chat-messages'].innerHTML, /Existing content/);
    assert.match(app.elements['chat-messages'].textContent, /Chưa tải được hội thoại/);
    assert.equal(app.elements['btn-send'].disabled, false);
  }
});

test('older history completion cannot replace a newer selection even when transport ignores abort', async () => {
  const first = deferred(), second = deferred();
  const app = setup(url => url.includes('/11/') ? first.promise : url.includes('/22/') ? second.promise : chatAnswer(22));
  const a = app.sessions[0].trigger('click');
  const b = app.sessions[1].trigger('click');
  assert.equal(app.requests[0].options.signal.aborted, true);
  second.resolve(history(22, [{role: 'ASSISTANT', content: 'Newer history', sources: [{document_title: 'Newer source', chunk_id: 22, similarity: .8}]}]));
  await b;
  first.resolve(history(11, [{role: 'ASSISTANT', content: 'Stale history', sources: [{document_title: 'Stale source', chunk_id: 11, similarity: .8}]}]));
  await a;
  assert.match(app.elements['chat-messages'].innerHTML, /Newer history/);
  assert.doesNotMatch(app.elements['chat-messages'].innerHTML, /Stale history/);
  assert.match(app.elements['citations-body'].innerHTML, /Newer source/);
  assert.doesNotMatch(app.elements['citations-body'].innerHTML, /Stale source/);
  assert.equal(app.sessions[1].getAttribute('aria-pressed'), 'true');
  assert.equal(app.sessions[0].getAttribute('aria-pressed'), 'false');
  await app.send('Continue newer history');
  assert.equal(JSON.parse(app.requests.at(-1).options.body).session_id, 22);
});

test('new chat invalidates pending history and a late completion cannot resurrect it', async () => {
  const pending = deferred();
  const app = setup(url => url.includes('/messages/') ? pending.promise : chatAnswer(33));
  const loaded = app.sessions[0].trigger('click');
  app.elements['btn-new-chat'].trigger('click');
  assert.equal(app.requests[0].options.signal.aborted, true);
  pending.resolve(history(11, [{role: 'ASSISTANT', content: 'Must not return'}]));
  await loaded;
  assert.match(app.elements['chat-messages'].innerHTML, /Bắt đầu cuộc trò chuyện mới/);
  assert.doesNotMatch(app.elements['chat-messages'].innerHTML, /Must not return/);
  assert.equal(app.elements['chat-messages'].getAttribute('aria-busy'), null);
  assert.equal(app.elements['btn-send'].disabled, false);
  await app.send('Start again');
  assert.equal(JSON.parse(app.requests.at(-1).options.body).session_id, null);
});

test('chat submission is blocked while history is loading and keyboard history activation works', async () => {
  const pending = deferred(); const app = setup(() => pending.promise); let prevented = false;
  app.sessions[0].trigger('keydown', {key: 'Enter', preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  await app.send('Do not attach question to the wrong history');
  assert.equal(app.requests.length, 1);
  pending.resolve(history(11, []));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(app.elements['btn-send'].disabled, false);
});

test('network failure releases busy state and does not replace current content', async () => {
  const app = setup(() => Promise.reject(new Error('offline network failure')));
  app.elements['chat-messages'].innerHTML = '<p>Existing network-safe content</p>';
  await app.sessions[0].trigger('click');
  assert.match(app.elements['chat-messages'].innerHTML, /Existing network-safe content/);
  assert.match(app.elements['chat-messages'].textContent, /Chưa tải được hội thoại/);
  assert.equal(app.elements['chat-messages'].getAttribute('aria-busy'), null);
  assert.equal(app.elements['btn-send'].disabled, false);
  assert.equal(app.timers.size, 0);
});

test('history timeout aborts the transport and preserves content with a retry warning', async () => {
  const app = setup((url, options) => new Promise((resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(Object.assign(new Error('Request aborted'), {name: 'AbortError'})));
  }));
  app.elements['chat-messages'].innerHTML = '<p>Keep this on timeout</p>';
  const loaded = app.sessions[0].trigger('click');
  assert.equal(app.timers.size, 1);
  [...app.timers.values()][0]();
  await loaded;
  assert.equal(app.requests[0].options.signal.aborted, true);
  assert.match(app.elements['chat-messages'].innerHTML, /Keep this on timeout/);
  assert.match(app.elements['chat-messages'].textContent, /Chưa tải được hội thoại/);
  assert.equal(app.elements['chat-messages'].getAttribute('aria-busy'), null);
  assert.equal(app.elements['btn-send'].disabled, false);
  assert.equal(app.timers.size, 0);
});

test('citation numeric metadata is escaped if a stored source contains hostile strings', async () => {
  const app = setup(() => history(11, [{role: 'ASSISTANT', content: 'Safe answer', sources: [{
    document_title: 'Stored metadata', similarity: .8,
    chunk_id: '<img src=x onerror=alert(1)>', page_number: '<script>alert(2)</script>',
  }]}]));
  await app.sessions[0].trigger('click');
  assert.doesNotMatch(app.elements['citations-body'].innerHTML, /<img |<script>/);
  assert.match(app.elements['citations-body'].innerHTML, /&lt;img /);
  assert.match(app.elements['citations-body'].innerHTML, /&lt;script&gt;/);
});
