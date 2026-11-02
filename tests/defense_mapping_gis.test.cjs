// Execute shipped template scripts against offline DOM/fetch/Leaflet boundaries.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const hostile = '<img src=x onerror="globalThis.attacked=true">\'&';
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const unescapeAttribute = value => value.replace(/&(?:amp|lt|gt|quot|#39);/g, entity => ({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&#39;':"'"}[entity]));
class Element {
  constructor() { this.children=[]; this.listeners={}; this.style={}; this.dataset={}; this.value=''; this.disabled=false; this.attributes={}; this._html=''; this._text=''; this.classList={add(){},remove(){}}; }
  set innerHTML(value) {
    this.children=[]; this._html=String(value); this._text=''; this.parsedButtons=[];
    for(const match of this._html.matchAll(/<button\b([^>]*)>/g)) {
      const button=new Element();
      for(const attribute of match[1].matchAll(/([\w-]+)=(?:"([^"]*)"|'([^']*)')/g)) button.setAttribute(attribute[1],unescapeAttribute(attribute[2] ?? attribute[3]));
      this.parsedButtons.push(button);
    }
  }
  get innerHTML() { return this._html + this.children.map(c => c.innerHTML).join(''); }
  set textContent(value) { this.children=[]; this._text=String(value ?? ''); this._html=escape(value); }
  get textContent() { return this._text + this.children.map(c=>c.textContent).join(''); }
  set innerText(value) { this.textContent=value; }
  get innerText() { return this.textContent; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.innerHTML=''; children.forEach(c=>this.appendChild(c)); }
  setAttribute(key,value) { this.attributes[key]=String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  addEventListener(type,fn) { this.listeners[type]=fn; }
  trigger(type) { return this.listeners[type]?.call(this,{preventDefault(){}}); }
}
function scriptFor(file) {
  return [...fs.readFileSync(path.join(__dirname,'../templates',file),'utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
}
function setup(file, responder, extras={}) {
  const elements={}, requests=[], timers=[], errors=[], popups=[]; let ready;
  const get = id => elements[id] ||= new Element();
  const context={
    document:{getElementById:get, createElement:()=>new Element(), querySelector:()=>({value:'csrf'}), querySelectorAll(selector){
      const visit=node=>[...(node.parsedButtons||[]),...node.children.flatMap(visit)];
      return selector==='.btn-accept-ai'?Object.values(elements).flatMap(visit).filter(node=>node.getAttribute('class')==='btn-accept-ai'):[];
    }, addEventListener(type,fn){ready=fn;}},
    window:{location:{reload(){timers.push('reload');}}},
    fetch:async(url,options={})=>{requests.push({url,options}); return {json:async()=>responder(url,options)};},
    FormData:class {}, alert(message){errors.push(message);}, console:{error(...args){errors.push(args);}},
    setTimeout(fn){timers.push(fn);}, ...extras,
  };
  vm.createContext(context);
  vm.runInContext(scriptFor(file).replaceAll('{{ active_workspace.id|escapejs }}','page-workspace'),context);
  if (ready) ready();
  return {context,get,requests,timers,errors,popups};
}
async function settle() { for(let i=0;i<12;i++) await Promise.resolve(); }
function safeHTML(html) { assert.doesNotMatch(html, /<img\s|<script\s|data-src="<|data-conf='[^']*'&/i); assert.match(html,/&lt;img/); }

test('integration preview renders hostile headers, cells and warnings as literal text',async()=>{
  const app=setup('integration/import.html',()=>({status:'success',data:{is_valid:true,total_rows:1,columns:[hostile],detected_types:{[hostile]:'STRING'},warnings:[hostile],sample_rows:[{row_number:1,raw_data:{[hostile]:hostile}}]}}));
  await app.context.runPreview();
  for(const id of ['res-columns-chips','res-table-head','res-table-body','res-warnings-box']) safeHTML(app.get(id).innerHTML);
});

test('mapping preview renders raw/canonical values and validation errors as text',async()=>{
  const app=setup('mapping/mapping_studio.html',()=>({success:true,data:{is_valid:false,invalid_count:1,sample_count:1,transformed_samples:[{row_number:1,raw_input:{name:hostile},canonical_output:{name:hostile},is_valid:false,errors:[{message:hostile}]}]}}));
  app.get('btnRunPreview').trigger('click'); await settle();
  safeHTML(app.get('previewTableWrapper').innerHTML);
});

test('mapping suggestions safely render text and quoted configuration attributes',async()=>{
  const app=setup('mapping/mapping_studio.html',()=>({success:true,suggestions:[{source_field:hostile,suggested_target_field:hostile,suggested_rule_type:'VALUE_MAPPING',confidence:.8,reason:hostile,transformation_config:{value_map:{[hostile]:hostile}}}]}));
  app.get('source-columns-data').textContent='[]'; app.get('column-stats-data').textContent='{}';
  app.get('btnAiSuggest').trigger('click'); await settle();
  safeHTML(app.get('aiSuggestionsList').innerHTML);
  const [button]=app.context.document.querySelectorAll('.btn-accept-ai');
  assert.ok(button,'the escaped suggestion retains its usable accept button');
  button.trigger('click'); await settle();
  const payload=JSON.parse(app.requests.at(-1).options.body);
  assert.equal(payload.source_field,hostile);
  assert.equal(payload.target_field,hostile);
  assert.deepEqual(payload.transformation_config,{value_map:{[hostile]:hostile}});
});

for(const [inserted,failed] of [[1,1],[0,2]]) test(`partial import preserves ${failed} rejection diagnostics with ${inserted} saved rows`,async()=>{
  const app=setup('mapping/mapping_studio.html',()=>({success:true,data:{status:'PARTIAL',target_entity:'Task',inserted_count:inserted,failed_count:failed,errors:[{row:2,errors:[{message:hostile}]}]}}));
  app.get('btnConfirmApply').trigger('click'); await settle();
  const result=app.get('applyStatusBox');
  assert.doesNotMatch(result.innerHTML,/Nhập Dữ liệu Thành công!/);
  assert.match(result.textContent,new RegExp(`đã lưu ${inserted}; bị từ chối ${failed}`)); safeHTML(result.innerHTML);
  assert.equal(app.timers.length,0,'partial diagnostics must not disappear via forced reload');
  assert.equal(app.get('btnConfirmApply').disabled,false);
});

function leaflet(popups) {
  const layer=()=>({addTo(){return this;},clearLayers(){},addLayer(){return this;},bindPopup(content){popups.push(content instanceof Element?content.innerHTML:content);return this;}});
  return {map:()=>({addLayer(){},removeLayer(){},setView(){}}),tileLayer:layer,layerGroup:layer,marker:layer,circleMarker:layer,circle:layer,polyline:layer,divIcon:options=>options};
}
function gisResponder(url) {
  if(url.includes('nearby-technicians')) return {status:'success',data:{ticket_coordinates:[106.7,10.7],search_radius_km:10,total_candidates:1,candidates:[{coordinates:[106.7,10.7],full_name:hostile,code:hostile,formatted_rate:hostile,distance_km:1,current_workload_score:1,skills:[hostile]}]}};
  if(url.includes('/revenue/')) return {status:'success',data:{branch_rankings:[{name:hostile,revenue:1,revenue_share_pct:100,order_count:1}]}};
  const properties={name:hostile,address:hostile,code:hostile,region:hostile,formatted_revenue:hostile,order_count:1,average_order_value:1,customer_segment:'STANDARD',ticket_id:1,request_number:hostile,title:hostile,category_display:hostile,customer_name:hostile,customer_address:hostile,assigned_employee_name:hostile,priority:'MEDIUM',status_display:hostile,full_name:hostile,phone:hostile,formatted_rate:hostile,current_workload_score:1,is_available:true,skills:[hostile]};
  return {status:'success',data:{metadata:{total_spatial_revenue:1},features:[{geometry:{coordinates:[106.7,10.7]},properties}]}};
}
for(const domain of ['retail','service_ops']) {
  test(`${domain} GIS binds every initial/filter/proximity fetch to page workspace`,async()=>{
    const popups=[]; const app=setup(`${domain}/gis.html`,gisResponder,{L:leaflet(popups)}); await settle();
    if(domain==='service_ops') { app.get('filter-category').trigger('change'); app.context.window.inspectNearbyTechnicians(1); }
    else app.get('segment-select').trigger('change');
    await settle(); assert.ok(app.requests.length>=4);
    for(const {options} of app.requests) assert.equal(options.headers['X-Workspace-ID'],'page-workspace');
  });
  test(`${domain} GIS popup/ranking/proximity names and addresses cannot become markup`,async()=>{
    const popups=[]; const app=setup(`${domain}/gis.html`,gisResponder,{L:leaflet(popups)}); await settle();
    assert.equal(popups.length,2,'both real layer handlers rendered a popup'); popups.forEach(safeHTML);
    if(domain==='service_ops') { app.context.window.inspectNearbyTechnicians(1); await settle(); safeHTML(app.get('proximity-content').innerHTML); }
    else safeHTML(app.get('branch-ranking-list').innerHTML);
    assert.deepEqual(app.errors,[]);
  });
}
