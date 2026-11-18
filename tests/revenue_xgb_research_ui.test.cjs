const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
    constructor() { this.children = []; this.textContent = ''; this.disabled = false; }
    append(...elements) { this.children.push(...elements); }
    replaceChildren(...elements) { this.children = elements; }
    setAttribute() {}
    addEventListener(name, handler) { this[name] = handler; }
    querySelector() { return {value:'token'}; }
}
test('renders three actual metrics, observed rows and forecasts as tables', async () => {
    const ids = Object.fromEntries(['form','run','status','result'].map(k => ['revenue-research-'+k, new Element()]));
    ids['revenue-research-form'].action = '/noibo/mo-phong-ai/doanh-thu-xgboost/?workspace_id=verified';
    const metric = {mae: 10, rmse: 20};
    const data = {start:'2026-01-01',end:'2026-05-10',periods:130,observed:102,imputed:28,
        training_periods:102,training_end:'2026-04-12',holdout_start:'2026-04-13',holdout_end:'2026-05-10',
        holdout_observed:2,holdout_periods:28,warning:'Thử nghiệm tham khảo',
        metrics:{xgboost:metric,ma7:metric,lag7:metric},
        holdout_rows:[{date:'2026-05-10',origin:'2026-04-26',step:14,actual:20,prediction:10,ma7:10,naive:10}],
        forecast:[{date:'2026-05-11',value:15}]};
    const document = {getElementById:id=>ids[id],createElement:()=>new Element()};
    let sent;
    vm.runInNewContext(fs.readFileSync('static/js/revenue_xgb_research.js','utf8'), {document,Intl,URLSearchParams,
        fetch:async(url,options)=>{sent={url,options};return {ok:true,json:async()=>data};}});
    await ids['revenue-research-form'].submit({preventDefault(){}});
    assert.equal(sent.url, ids['revenue-research-form'].action);
    assert.equal(sent.options.headers['X-CSRFToken'],'token');
    const result = ids['revenue-research-result'];
    assert.equal(result.children.length, 6);
    assert.equal(result.children.filter(node=>node.className==='demo-scroll').length, 3);
    assert.match(ids['revenue-research-status'].textContent,/Đã chạy/);
    assert.equal(ids['revenue-research-run'].disabled,false);
});
