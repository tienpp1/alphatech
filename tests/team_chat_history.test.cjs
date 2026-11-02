/* Executes shipped chat JS. Only DOM/HTTP/timers are controlled test boundaries. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
    constructor() { this.dataset={}; this.children=[]; this.listeners={}; this.attributes={}; this.value=''; this.scrollTop=100; this.clientHeight=200; this.disabled=false; }
    get scrollHeight() { return this.children.length * 20; }
    addEventListener(name, fn) { this.listeners[name]=fn; }
    setAttribute(name, value) { this.attributes[name]=value; }
    appendChild(el) { this.children.push(el); }
    insertBefore(el, next) { const i=this.children.indexOf(next); if(i<0)this.children.push(el);else this.children.splice(i,0,el); }
    querySelector(selector) {
        if(selector.includes('csrf')) return {value:'csrf'};
        const match=selector.match(/data-msg-id="(\d+)"/);
        return match ? this.children.find(el=>Number(el.dataset.msgId)===Number(match[1])) : null;
    }
    querySelectorAll() { return this.children.filter(el=>el.dataset.msgId); }
}
const response = data => ({ok:true,status:200,redirected:false,json:async()=>data});
const message = id => ({id,is_me:false,sender_name:'<img onerror=alert(1)>',message:'<script>literal '+id+'</script>',created_at:'12:00 02/11'});
const page = (start,end,hasOlder=true) => ({ok:true,status:'success',workspace_id:'workspace-a',messages:Array.from({length:Math.max(0,end-start+1)},(_,i)=>message(start+i)),latest_id:end>=start?end:0,oldest_id:end>=start?start:0,has_older:hasOlder});
const tick = async()=>{for(let i=0;i<4;i++)await new Promise(resolve=>setImmediate(resolve));};
function harness() {
    const ids={};
    ['chatMessagesStream','chatForm','chatInputMessage','btnSendChat','chatConnectionStatus','chatSendStatus','chatLoadOlder','chatHistoryStatus'].forEach(id=>ids[id]=new Element());
    ids.chatMessagesStream.dataset={workspaceId:'workspace-a',latestId:'110',oldestId:'61'};
    ids.chatLoadOlder.dataset.hasOlder='true';
    for(let id=61;id<=110;id++){const row=new Element();row.dataset.msgId=id;ids.chatMessagesStream.appendChild(row);}
    let handler=async()=>response(page(1,0,false)), seq=0;
    const calls=[],timers=new Map(),events={},documentEvents={};
    const document={hidden:false,getElementById:id=>ids[id]||null,createElement:()=>new Element(),addEventListener:(n,f)=>documentEvents[n]=f};
    vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/js/internal_team_chat.js'),'utf8'), {
        document,window:{addEventListener:(n,f)=>events[n]=f},AbortController,
        setTimeout:(fn,ms)=>{timers.set(++seq,{fn,ms});return seq;},clearTimeout:id=>timers.delete(id),
        fetch:async(url,options)=>{calls.push({url,options});return handler(url,options);},
    });
    return {ids,calls,timers,events,document,documentEvents,setHandler:h=>handler=h};
}
const rows = h => h.ids.chatMessagesStream.children.map(el=>Number(el.dataset.msgId));
function older(h) { assert.equal(typeof h.ids.chatLoadOlder.listeners.click,'function','Load older must have an executable handler');return h.ids.chatLoadOlder.listeners.click(); }

test('older pages prepend safely, preserve scroll/draft and never move forward polling backwards',async()=>{
    const h=harness();await tick();h.ids.chatMessagesStream.scrollTop=100;h.ids.chatInputMessage.value='draft unchanged';
    h.setHandler(async url=>response(url.includes('before_id=61')?page(11,60):page(111,111,false)));
    await older(h);
    assert.deepEqual(rows(h),Array.from({length:100},(_,i)=>i+11));
    assert.equal(h.ids.chatMessagesStream.scrollTop,1100);
    assert.equal(h.ids.chatInputMessage.value,'draft unchanged');
    assert.equal(h.ids.chatMessagesStream.children[0].children[1].children[1].textContent,'<script>literal 11</script>');
    h.events.online();await tick();
    assert.ok(h.calls.at(-1).url.includes('since_id=110'));
    assert.equal(rows(h).at(-1),111);
    h.setHandler(async()=>response(page(1,10,false)));await older(h);
    assert.ok(h.calls.at(-1).url.includes('before_id=11'));
    assert.deepEqual(rows(h),Array.from({length:111},(_,i)=>i+1));
    assert.equal(h.ids.chatLoadOlder.disabled,true);
    const count=h.calls.length;await older(h);assert.equal(h.calls.length,count);
});

test('history failure retains rows, cursor and draft; retry works; one request in flight',async()=>{
    const h=harness();await tick();h.ids.chatInputMessage.value='unsent';
    h.setHandler(async()=>{throw Error('network');});await older(h);
    assert.equal(rows(h).length,50);assert.equal(h.ids.chatLoadOlder.disabled,false);
    assert.match(h.ids.chatHistoryStatus.textContent,/thử lại/);
    let release;h.setHandler(()=>new Promise(resolve=>release=resolve));
    const pending=older(h);const count=h.calls.length;await older(h);assert.equal(h.calls.length,count);
    assert.ok(h.calls.at(-1).url.includes('before_id=61'));
    release(response(page(11,60)));await pending;
    assert.equal(rows(h).length,100);assert.equal(h.ids.chatInputMessage.value,'unsent');
    assert.equal(h.ids.chatLoadOlder.attributes['aria-busy'],'false');
});

test('history overlap is deduplicated when its row already exists',async()=>{
    const h=harness();await tick();const extra=new Element();extra.dataset.msgId=60;h.ids.chatMessagesStream.insertBefore(extra,h.ids.chatMessagesStream.children[0]);
    h.setHandler(async()=>response(page(11,60)));await older(h);
    assert.equal(rows(h).length,100);assert.equal(rows(h).filter(id=>id===60).length,1);
});

test('hidden tabs do not load history and denial stops all controls and pending successful responses',async()=>{
    const h=harness();await tick();h.document.hidden=true;const count=h.calls.length;await older(h);assert.equal(h.calls.length,count);
    h.document.hidden=false;let release;
    h.setHandler(url=>url.includes('before_id')?new Promise(resolve=>release=resolve):Promise.resolve({ok:false,status:403}));
    const pending=older(h);h.events.online();await tick();
    release(response(page(11,60)));await pending;
    assert.equal(rows(h).length,50);assert.equal(h.ids.chatLoadOlder.disabled,true);assert.equal(h.ids.btnSendChat.disabled,true);
    assert.match(h.ids.chatHistoryStatus.textContent,/Quyền truy cập/);
    const denied=h.calls.length;await older(h);h.events.online();assert.equal(h.calls.length,denied);
});

test('forward multi-message delivery still scrolls to the last new message when already at bottom',async()=>{
    const h=harness();await tick();h.ids.chatMessagesStream.scrollTop=800;
    h.setHandler(async()=>response(page(111,112,false)));h.events.online();await tick();
    assert.equal(rows(h).at(-1),112);
    assert.equal(h.ids.chatMessagesStream.scrollTop,h.ids.chatMessagesStream.scrollHeight);
});

test('a forward poll can finish during older loading without losing its separate cursor',async()=>{
    const h=harness();await tick();let release;
    h.ids.chatInputMessage.value='keep while reading';
    h.setHandler(url=>url.includes('before_id')?new Promise(resolve=>release=resolve):Promise.resolve(response(page(111,111,false))));
    const pending=older(h);h.events.online();await tick();
    assert.equal(rows(h).at(-1),111);
    release(response(page(11,60)));await pending;
    h.events.online();await tick();
    assert.ok(h.calls.at(-1).url.includes('since_id=111'));
    assert.equal(rows(h).length,101);
    assert.equal(h.ids.chatInputMessage.value,'keep while reading');
});

test('wrong-workspace or invalid history responses cannot corrupt cursor or visible history',async()=>{
    const h=harness();await tick();
    for(const data of [{...page(11,60),workspace_id:'foreign'},page(70,119),{...page(11,60),messages:[message(20),message(19)]}]){
        h.setHandler(async()=>response(data));await older(h);assert.equal(rows(h).length,50);
        assert.ok(h.calls.at(-1).url.includes('before_id=61'));
        assert.equal(h.ids.chatLoadOlder.disabled,false);
    }
});
