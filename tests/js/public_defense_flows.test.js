const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '../..');
const template = name => fs.readFileSync(path.join(root, 'templates/public', name), 'utf8');
const scripts = name => [...template(name).matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const shell = scripts('base_public.html').find(s => s.includes('function toggleMobileNav'));
const checkout = scripts('checkout.html').find(s => s.includes('function setDeliveryMethod'));
const products = scripts('products.html').find(s => s.includes('function quickAddToCart'));
const homeScript = scripts('home.html').find(s => s.includes('function quickAddToCart'));
const homeQuickAdd = homeScript.slice(homeScript.indexOf('function quickAddToCart'));
const escape = text => String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
class Element {
  constructor(tag = 'div') { this.tag = tag; this.children = []; this.attrs = {}; this.listeners = {}; this.style = {}; this.value = ''; this.hidden = false; this.disabled = false; this.classList = {add(){}, remove(){}, contains(){return false;}}; }
  set textContent(value) { this.text = String(value); this.html = null; this.children = []; }
  get textContent() { return (this.text || '') + this.children.map(c => c.textContent).join(''); }
  set innerHTML(value) { this.html = value; this.text = ''; this.children = []; }
  get innerHTML() { return this.html ?? (escape(this.text || '') + this.children.map(c => c.outerHTML).join('')); }
  get outerHTML() { return `<${this.tag}${Object.entries(this.attrs).map(([k,v]) => ` ${k}="${escape(v)}"`).join('')}>${this.innerHTML}</${this.tag}>`; }
  setAttribute(k,v) { this.attrs[k] = String(v); }
  removeAttribute(k) { delete this.attrs[k]; }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.append(child); return child; }
  replaceChildren(...children) { this.text = ''; this.html = null; this.children = children; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatchEvent(event) { for (const fn of this.listeners[event.type] || []) fn(event); return true; }
}
function harness(withCheckout = false) {
  const nodes = new Map(), document = new Element(), calls = [], timers = new Map(); let timer = 0;
  const node = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  const radios = [{value:'HOME_DELIVERY',checked:true}, {value:'STORE_PICKUP',checked:false}];
  Object.assign(document, {cookie:'csrftoken=test', getElementById:node, createElement:tag => new Element(tag),
    querySelector:() => radios.find(r => r.checked), querySelectorAll:selector => selector.includes('delivery_method') ? radios : []});
  const context = {document, console, FormData, AbortController, URL, encodeURIComponent, location:{href:'https://example.test/thanh-toan/'},
    window:{location:{href:'https://example.test/thanh-toan/'}}, navigator:{}, CustomEvent:class {constructor(type, options={}) {this.type=type;this.detail=options.detail;}},
    setTimeout(fn) {timers.set(++timer,fn);return timer;},clearTimeout(id){timers.delete(id);},
    fetch(url,options={}) {return new Promise((resolve,reject) => {
      if(options.signal) options.signal.addEventListener('abort',()=>reject(Error('aborted')));
      calls.push({url,options,resolve,reject});
    });}};
  vm.createContext(context); vm.runInContext(shell,context);
  if (withCheckout) vm.runInContext(checkout,context);
  return {context,node,calls,document,timers};
}
const flush = async () => {for(let i=0;i<20;i++) await Promise.resolve();};
const summary = (quantity=2) => ({items:quantity ? [{product_id:1,name:'TEST cable',quantity,unit_price:95000,line_total:95000*quantity,formatted_unit_price:'95.000₫',formatted_line_total:'190.000₫',image_url:null}] : [],
  total_quantity:quantity,items_count:quantity?1:0,subtotal:95000*quantity,formatted_subtotal:quantity?'190.000₫':'0₫',shipping_fee:quantity?30000:0,formatted_shipping_fee:quantity?'30.000₫':'Miễn phí',total_amount:quantity?220000:0,formatted_total_amount:quantity?'220.000₫':'0₫',progress_pct:3,is_free_shipping:!quantity,formatted_remaining:'4.810.000₫'});
const reply = (call,data,ok=true) => call.resolve({ok,json:async()=>data});

test('drawer treats product names and unsafe image URLs as data', () => {
  const h=harness(), cart=summary();cart.items[0].name='TEST <img src=x onerror="alert(1)">';cart.items[0].image_url='javascript:alert(1)';
  h.context.renderCyberCart(cart);
  assert.doesNotMatch(h.node('cyber-cart-body').innerHTML, /<img src=x|src="javascript:/);
  assert.match(h.node('cyber-cart-body').innerHTML, /&lt;img/);
});

test('drawer changes block checkout immediately and refresh all review fields without clearing draft', async () => {
  const h=harness(true);h.node('name').value='Draft customer';h.node('summary-grand-total').textContent='125.000₫';
  h.context.cyberCartUpdateQty(1,2);
  assert.equal(h.node('btn-place-order').disabled,true);
  reply(h.calls[0],{success:true,cart:summary()});await flush();
  assert.equal(h.calls[1].options.method || 'GET','GET');reply(h.calls[1],summary());await flush();
  assert.equal(h.node('summary-grand-total').textContent,'220.000₫');
  assert.equal(h.node('summary-subtotal').textContent,'190.000₫');
  assert.match(h.node('checkout-review-items').textContent,/TEST cable/);
  assert.match(h.node('checkout-review-items').textContent,/2/);
  assert.equal(h.node('name').value,'Draft customer');assert.equal(h.node('btn-place-order').disabled,false);
});

test('ambiguous mutation never replays POST and submit stays blocked until authoritative GET', async () => {
  const h=harness(true);h.context.cyberCartUpdateQty(1,2);h.calls[0].reject(Error('lost response'));await flush();
  assert.equal(h.node('btn-place-order').disabled,true);
  assert.equal(h.calls.length,2);assert.equal(h.calls[1].options.method || 'GET','GET');
  assert.equal(h.calls[1].options.cache,'no-store');
  h.calls[1].reject(Error('offline'));await flush();assert.equal(h.node('btn-place-order').disabled,true);
  h.node('checkout-summary-retry').dispatchEvent({type:'click'});reply(h.calls[2],summary());await flush();
  assert.equal(h.node('btn-place-order').disabled,false);
  assert.equal(h.calls.filter(c=>c.options.method==='POST').length,1);
});

test('empty authoritative cart blocks checkout and removes obsolete review lines', async () => {
  const h=harness(true);h.context.cyberCartRemoveItem(1);reply(h.calls[0],{success:true,cart:summary(0)});await flush();reply(h.calls[1],summary(0));await flush();
  assert.equal(h.node('btn-place-order').disabled,true);assert.doesNotMatch(h.node('checkout-review-items').textContent,/TEST cable/);
});

test('rejected POST reconciles unchanged cart rather than fabricating an update', async () => {
  const h=harness(true);h.context.cyberCartUpdateQty(1,9);reply(h.calls[0],{error:'forbidden'},false);await flush();
  assert.equal(h.node('btn-place-order').disabled,true);const old=summary(1);old.formatted_total_amount='125.000₫';old.formatted_subtotal='95.000₫';old.total_amount=125000;
  reply(h.calls[1],old);await flush();assert.equal(h.node('summary-grand-total').textContent,'125.000₫');
});

test('quick-add failed POST reports error without GET mutation or navigation', async () => {
  const h=harness();vm.runInContext(products,h.context);const before=h.context.window.location.href;
  h.context.quickAddToCart(1,'TEST');h.calls[0].reject(Error('offline'));await flush();
  assert.equal(h.calls.length,1);assert.equal(h.context.window.location.href,before);
  assert.match(h.node('cart-toast-msg').textContent,/không|Không|Chưa/);
});

for (const [page, source] of [['catalog', products], ['home', homeQuickAdd]]) {
  test(`${page} quick-add uses CSRF POST and never retries or reports success on rejection`, async () => {
    for (const failure of ['network', 'http', 'rejected']) {
      const h=harness();vm.runInContext(source,h.context);const before=h.context.window.location.href;
      h.context.quickAddToCart(1,'TEST');assert.equal(h.calls[0].options.method,'POST');
      assert.equal(h.calls[0].options.headers['X-CSRFToken'],'test');
      if(failure==='network')h.calls[0].reject(Error('offline'));
      else reply(h.calls[0],{success:false},failure!=='http');
      await flush();assert.equal(h.calls.length,1);assert.equal(h.context.window.location.href,before);
      assert.match(h.node('cart-toast-msg').textContent,/không|Không|Chưa/);
    }
  });
}

test('an older summary cannot unlock submit after a newer drawer mutation starts', async () => {
  const h=harness(true);h.context.setDeliveryMethod('STORE_PICKUP');
  h.context.cyberCartUpdateQty(1,2);reply(h.calls[0],summary());await flush();
  let blocked=false;h.node('checkout-form').dispatchEvent({type:'submit',preventDefault(){blocked=true;}});
  assert.equal(blocked,true);assert.equal(h.node('btn-place-order').disabled,true);
  reply(h.calls[1],{success:true,cart:summary()});await flush();
  assert.match(h.calls[2].url,/delivery_method=STORE_PICKUP/);
  const pickup=summary();pickup.shipping_fee=0;pickup.total_amount=190000;pickup.formatted_total_amount='190.000₫';
  reply(h.calls[2],pickup);await flush();assert.equal(h.node('summary-grand-total').textContent,'190.000₫');
  blocked=false;h.node('checkout-form').dispatchEvent({type:'submit',preventDefault(){blocked=true;}});assert.equal(blocked,false);
});

test('mutation timeout never replays POST and concurrent clicks are not submitted twice', async () => {
  const h=harness(true);h.context.cyberCartUpdateQty(1,2);h.context.cyberCartUpdateQty(1,3);
  assert.equal(h.calls.length,1);[...h.timers.values()][0]();await flush();
  assert.equal(h.calls[0].options.signal.aborted,true);assert.equal(h.calls.length,2);
  assert.equal(h.node('btn-place-order').disabled,true);reply(h.calls[1],summary());await flush();
  assert.equal(h.node('btn-place-order').disabled,false);assert.equal(h.calls.filter(c=>c.options.method==='POST').length,1);
});

test('malformed full review and inconsistent amounts stay unknown until retry', async () => {
  for(const bad of [{...summary(),items:null},{...summary(),total_amount:999},
    {...summary(),items:[{...summary().items[0],quantity:0}]}]) {
    const h=harness(true);h.context.cyberCartUpdateQty(1,2);reply(h.calls[0],{success:true,cart:summary()});await flush();
    reply(h.calls[1],bad);await flush();assert.equal(h.node('btn-place-order').disabled,true);
    assert.equal(h.node('checkout-summary-retry').hidden,false);
  }
});
