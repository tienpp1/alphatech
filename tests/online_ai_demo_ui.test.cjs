const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const stamp = '2026-11-18T01:23:45.678+00:00';
const untrusted = '<img src=x onerror=alert(1)>';
const action = 'https://example.test/noibo/mo-phong-ai/run/?workspace_id=46b86bdd-d16f-4f11-abe2-8ca8f5ca4303';
const caveat = 'Kịch bản và dữ liệu mẫu đã biết trước. Đây không phải kiểm thử mù hay bằng chứng thương mại.';

class Element {
    constructor(tag = '') {
        this.tagName = tag;
        this.children = [];
        this.attributes = {};
        this.hidden = false;
        this.disabled = false;
        this.value = '';
        this.text = '';
    }
    set innerHTML(_) { assert.fail('Use DOM nodes and textContent; no HTML insertion'); }
    get textContent() { return this.text + this.children.map(node => node.textContent).join(' '); }
    set textContent(text) { this.text = String(text); this.children = []; }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener(name, callback) { this[name] = callback; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; this.text = ''; }
    querySelector(query) {
        assert.equal(query, '[name="csrfmiddlewaretoken"]');
        return {value: 'test-token'};
    }
}

function lab(fetch) {
    const elements = Object.fromEntries(
        ['form', 'case', 'run', 'panel', 'status', 'result', 'error', 'previous', 'caveat'].map(id => [id, new Element()]),
    );
    elements.form.action = action;
    elements.caveat.textContent = caveat;
    elements.case.value = 'retrieval';
    elements.case.selectedOptions = [{textContent: 'Truy xuất'}];
    elements.previous.hidden = true;
    elements.result.hidden = true;
    elements.error.hidden = true;
    const document = {
        getElementById: id => elements[id.replace(/^demo-/, '')],
        createElement: tag => new Element(tag),
    };
    vm.runInNewContext(fs.readFileSync('static/js/ai_demo_lab.js', 'utf8'),
        {document, fetch, URLSearchParams, Intl, Date});
    return {elements, submit: () => elements.form.submit({preventDefault() {}})};
}

function success(caseKey, data, executedAt = stamp) {
    return {
        ok: true, status: 200, redirected: false,
        json: async () => ({
            scope: 'SYNTHETIC_DEMO', case: caseKey, executed_at: executedAt,
            elapsed_seconds: 0.125, execution_mode: 'Chế độ mô phỏng', warnings: [untrusted], data,
        }),
    };
}

const retrieval = {
    answer: untrusted, query: 'Câu hỏi mẫu', source: 'SOP mô phỏng', embedding_dimension: 128,
    candidates: [
        {source: 'SOP mô phỏng', title: 'Quy trình mẫu', excerpt: untrusted,
            dense_similarity: 0.5, lexical_score: 0.7, similarity: 0.8},
    ],
};

test('posts a real CSRF form to the lab once and exposes an accessible busy state', async () => {
    const requests = [];
    let resolve;
    const page = lab((url, options) => {
        requests.push({url, options});
        return new Promise(done => { resolve = done; });
    });
    const {elements} = page;
    const run = page.submit();
    assert.equal(elements.run.disabled, true);
    assert.equal(elements.panel.attributes['aria-busy'], 'true');
    assert.match(elements.status.textContent, /Đang chạy/);
    await page.submit();
    assert.equal(requests.length, 1);
    const {url, options} = requests[0];
    assert.equal(url, action);
    assert.equal(options.method, 'POST');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.headers['X-CSRFToken'], 'test-token');
    assert.equal(String(options.body), 'case=retrieval');
    resolve(success('retrieval', retrieval));
    await run;
    assert.equal(elements.run.disabled, false);
    assert.equal(elements.panel.attributes['aria-busy'], 'false');
    assert.match(elements.status.textContent, /Hoàn tất/);
    assert.equal(elements.result.hidden, false);
    assert.match(elements.result.textContent, /không gọi LLM/i);
    assert.ok(elements.result.textContent.includes(caveat));
    assert.ok(elements.result.textContent.includes(untrusted));
    assert.ok(elements.result.textContent.includes(stamp));
});

test('busy, unavailable and connection errors keep only the prior success with original timestamp', async () => {
    let count = 0;
    const replies = [success('retrieval', retrieval), {ok: false, status: 409}, {ok: false, status: 503}, null];
    const {elements, submit} = lab(async () => {
        const response = replies[count++];
        if (!response) throw new Error(untrusted);
        return response;
    });
    await submit();
    const original = elements.result.textContent;
    assert.equal(elements.previous.hidden, true);
    for (const message of [/đang bận/i, /chưa thể/i, /kết nối/i]) {
        await submit();
        assert.equal(elements.previous.hidden, false);
        assert.match(elements.previous.textContent, /thành công trước/i);
        assert.ok(elements.previous.textContent.includes(stamp));
        assert.equal(elements.result.textContent, original);
        assert.equal(elements.error.hidden, false);
        assert.match(elements.error.textContent, message);
        assert.ok(!elements.error.textContent.includes(untrusted));
        assert.equal(elements.run.disabled, false);
    }
    assert.equal(count, 4);
});

test('redirects and mismatched results are never reported as successful', async () => {
    for (const response of [{redirected: true}, success('forecast', {})]) {
        const {elements, submit} = lab(async () => response);
        await submit();
        assert.equal(elements.result.hidden, true);
        assert.equal(elements.previous.hidden, true);
        assert.equal(elements.error.hidden, false);
        assert.equal(elements.run.disabled, false);
    }
});

test('forecast, mapping and schema-only approval render actual case values in readable tables', async () => {
    const weight = {distance: .5, workload: .5, skill: 0};
    const mapping = {entity: 'Customer', before: {demo: untrusted}, after: {}, errors: [], suggestions: []};
    const metrics = {mae: 1.5, rmse: 2};
    const cases = [
        ['forecast', {model: 'XGBOOST_DIRECT', calendar_mode: 'full', training_cutoff: '2025-08-06',
            holdout_rows: 146, scored_rows: 140, omitted_rows: 6, training_rows: 584, history_rows: 730,
            horizon: 14, blocks: 10, holdout_start: '2025-08-07', holdout_end: '2025-12-30',
            metrics: {xgboost: metrics, ma7: metrics, seasonal_naive_7: metrics},
            sample_rows: [{date: '2025-08-07', origin: '2025-08-06', step: 1,
                actual: 10, prediction: 11, ma7: 12, naive: 13, observed: true}]},
        [/146/, /140/, /584/, /MAE/, /RMSE/, /huấn luyện ngoại tuyến/i, /XGBOOST_DIRECT/]],
        ['mapping_pending', {...mapping, confirmation_status: 'PENDING'}, [/chưa xác nhận/i, /không có trường/i]],
        ['mapping_confirmed', {...mapping, confirmation_status: 'ACCEPTED',
            after: {customer_id: 'DEMO-KH-01'},
            errors: [{source_field: 'phan_khuc', target_field: 'segment', error: untrusted, rule_type: 'ENUM_MAP'}]},
        [/đã xác nhận mô phỏng/i, /DEMO-KH-01/, /phan_khuc/]],
        ['recommendation', {selected_candidate: 'Kỹ thuật viên A',
            candidates: [{name: 'Kỹ thuật viên A', distance_km: 2, active_tasks: 0, is_available: true,
                score: 85, weights: weight, subscores: {distance_score: 90, workload_score: 80,
                    skill_score: 0, availability_score: 100}}],
            tool: {name: 'dispatch_technician', required_permission: 'example.permission',
                classification: 'MUTATION', risk_level: 'HIGH', schema_valid: true, check_domain: false},
            approval_preview: ['Bước mô phỏng']},
        [/chỉ kiểm tra cấu trúc/i, /không thực thi/i, /dispatch_technician/, /85/, /0,5/]],
    ];
    for (const [caseKey, data, expected] of cases) {
        const {elements, submit} = lab(async () => success(caseKey, data));
        elements.case.value = caseKey;
        await submit();
        assert.equal(elements.error.hidden, true, caseKey);
        assert.ok(elements.result.textContent.includes(caveat), caseKey);
        for (const pattern of expected) assert.match(elements.result.textContent, pattern);
    }
});
