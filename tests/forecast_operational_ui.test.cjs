const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function page(payload) {
    const html = fs.readFileSync('templates/forecasting/index.html', 'utf8');
    const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
    let chart, request;
    const fields = {'forecast-chart-payload': {textContent: JSON.stringify(payload)}, forecastChart: {},
        modalTarget: {value: 'RETAIL_REVENUE'}, modalEstimators: {value: '10'}, modalDepth: {value: '2'},
        modalLR: {value: '.05'}, modalHorizon: {value: '3'}, modalDataMode: {value: 'operational'},
        btnSubmitTrain: {}, modalAlert: {style: {}}};
    const context = vm.createContext({
        document: {getElementById: id => fields[id], addEventListener: () => {}, cookie: ''},
        Chart: function(_, options) { chart = options; },
        fetch: async (_, options) => {request = JSON.parse(options.body); return {json: async () => ({success: false, error: 'not ready'})};},
        setTimeout: () => {}, location: {reload: () => {}}, console,
    });
    vm.runInContext(script, context);
    return {context, fields, chart: () => chart, request: () => request};
}

test('overlapping actual and forecast dates form a sorted unique date join', () => {
    const p = page({historical: [{date:'2026-11-17',value:8},{date:'2026-11-16',value:7}],
        forecast: [{date:'2026-11-17',predicted:10},{date:'2026-11-18',predicted:11}], show_prediction_intervals:false});
    p.context.initForecastChart();
    const chart = p.chart();
    assert.deepEqual([...chart.data.labels], ['2026-11-16','2026-11-17','2026-11-18']);
    assert.deepEqual([...chart.data.datasets[0].data], [7,8,null]);
    assert.deepEqual([...chart.data.datasets[1].data], [null,10,11]);
});

test('late actuals are never connected backwards to a stale forecast origin', () => {
    const p = page({historical:[{date:'2026-11-01',value:7},{date:'2026-11-17',value:99}],
        forecast:[{date:'2026-11-02',predicted:10}], show_prediction_intervals:false});
    p.context.initForecastChart();
    assert.deepEqual([...p.chart().data.datasets[1].data], [null,10,null]);
});

test('training explicitly submits chosen operational or historical mode', async () => {
    const p = page({});
    await p.context.submitTraining({preventDefault(){}});
    assert.equal(p.request().data_mode, 'operational');
    p.fields.modalDataMode.value = 'historical';
    await p.context.submitTraining({preventDefault(){}});
    assert.equal(p.request().data_mode, 'historical');
});
