'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup({historical = false, response, failure, pending = false} = {}) {
    const html = fs.readFileSync('templates/recommendations/index.html', 'utf8');
    const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1]
        .replaceAll('{{ active_workspace.id|escapejs }}', 'page-workspace');
    const elements = {
        'btn-evaluate-rules': {disabled: false},
        'evaluation-status': {textContent: ''},
        'include-historical-forecast': {checked: historical},
    };
    const calls = [];
    let reloads = 0, settle;
    const context = vm.createContext({
        document: {cookie: 'csrftoken=csrf-test', getElementById: id => elements[id] || null},
        location: {reload: () => reloads++},
        fetch: (url, options) => {
            calls.push({url, options});
            if (failure) return Promise.reject(new Error('network'));
            if (pending) return new Promise(resolve => { settle = resolve; });
            return Promise.resolve(response || {ok: true, json: async () => ({success: true})});
        },
    });
    vm.runInContext(script, context);
    return {context, elements, calls, reloads: () => reloads, settle: value => settle(value)};
}

test('evaluation explicitly sends historical opt-in and authorized page workspace', async () => {
    const page = setup({historical: true});
    await page.context.triggerEvaluation();
    const {options} = page.calls[0];
    assert.equal(options.method, 'POST');
    assert.equal(options.headers['X-Workspace-ID'], 'page-workspace');
    assert.equal(options.headers['X-CSRFToken'], 'csrf-test');
    assert.deepEqual(JSON.parse(options.body), {include_historical_forecast: true});
    assert.equal(page.reloads(), 1);
});

test('default evaluation does not silently enable historical analysis', async () => {
    const page = setup();
    await page.context.triggerEvaluation();
    assert.deepEqual(JSON.parse(page.calls[0].options.body), {include_historical_forecast: false});
});

test('concurrent evaluation click cannot submit duplicate POSTs', async () => {
    const page = setup({pending: true});
    const first = page.context.triggerEvaluation();
    await page.context.triggerEvaluation();
    assert.equal(page.calls.length, 1);
    assert.equal(page.elements['btn-evaluate-rules'].disabled, true);
    page.settle({ok: true, json: async () => ({success: true})});
    await first;
    assert.equal(page.elements['btn-evaluate-rules'].disabled, false);
});

test('network or HTTP failure has truthful feedback and no automatic replay', async () => {
    for (const fixture of [{failure: true}, {response: {ok: false}}]) {
        const page = setup(fixture);
        await page.context.triggerEvaluation();
        assert.equal(page.calls.length, 1);
        assert.equal(page.reloads(), 0);
        assert.match(page.elements['evaluation-status'].textContent, /Chưa xác nhận/);
        assert.equal(page.elements['btn-evaluate-rules'].disabled, false);
    }
});

test('application validation error remains literal user feedback', async () => {
    const message = '<img src=x onerror=alert(1)>';
    const page = setup({response: {ok: true, json: async () => ({success: false, error: message})}});
    await page.context.triggerEvaluation();
    assert.equal(page.elements['evaluation-status'].textContent, 'Đánh giá thất bại: ' + message);
    assert.equal(page.reloads(), 0);
});
