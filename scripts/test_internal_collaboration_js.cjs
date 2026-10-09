/* Deterministic client regressions: real scripts, fake transport and minimal DOM. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
class Element {
    constructor() { this.dataset={}; this.style={}; this.children=[]; this.listeners={}; this.value=''; this.scrollHeight=0; this.scrollTop=0; this.clientHeight=0; }
    addEventListener(name, fn) { this.listeners[name]=fn; }
    appendChild(el) { this.children.push(el); }
    insertBefore(el, next) { const i=this.children.indexOf(next); if(i<0)this.children.push(el);else this.children.splice(i,0,el); }
    replaceChildren(el) { this.children=[el]; }
    querySelector(selector) {
        if(selector.includes('csrf')) return {value:'test-csrf'};
        const m=selector.match(/data-msg-id="(\d+)"/);
        return m ? this.children.find(el=>Number(el.dataset.msgId)===Number(m[1])) : null;
    }
    querySelectorAll() { return this.children.filter(el=>el.dataset.msgId); }
}
function harness(file) {
    const ids={}; ['chatMessagesStream','chatForm','chatInputMessage','btnSendChat','chatConnectionStatus','chatSendStatus','bulletinLiveFeed','bulletinConnectionStatus'].forEach(id=>ids[id]=new Element());
    ids.chatMessagesStream.dataset={workspaceId:'test-ws',latestId:'10'};
    ids.bulletinLiveFeed.dataset={workspaceId:'test-ws',priority:'',canManage:'false'};
    const calls=[], timers=new Map(), events={}, documentEvents={};
    let seq=0, handler=async()=>({status:'success',workspace_id:'test-ws',messages:[],bulletins:[]});
    const document={hidden:false,getElementById:id=>ids[id]||null,createElement:()=>new Element(),addEventListener:(n,f)=>documentEvents[n]=f};
    vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/js',file),'utf8'), {
        document, window:{addEventListener:(n,f)=>events[n]=f}, AbortController,
        setTimeout:(fn,ms)=>{timers.set(++seq,{fn,ms});return seq;}, clearTimeout:id=>timers.delete(id),
        fetch:async(url,options)=>{calls.push({url,options});return handler(url,options);},
    });
    return {ids,calls,timers,events,document,documentEvents,setHandler:h=>handler=h};
}
const tick=async()=>{for(let i=0;i<4;i++)await new Promise(resolve=>setImmediate(resolve));};
const response=data=>({ok:true,status:200,redirected:false,json:async()=>data});
async function run() {
    // Initial mock intentionally invalid: retry must recover using real response schema.
    const h=harness('internal_team_chat.js'); await tick();
    h.setHandler(async(url,options)=>response(options.method==='POST' ? {ok:true,message_id:12,message:{text:'new'},created_at:'now'} : {ok:true,workspace_id:'test-ws',messages:[{id:11,message:'peer'},{id:12,message:'new'}]}));
    h.ids.chatInputMessage.value='new';
    await h.ids.chatForm.listeners.submit({preventDefault(){}}); await tick();
    assert.equal(h.ids.chatInputMessage.value,'');
    assert.ok(h.calls.some(c=>c.url.includes('since_id=10')), 'Sending ID12 must not skip unseen ID11');
    assert.deepEqual(h.ids.chatMessagesStream.children.map(el=>Number(el.dataset.msgId)),[11,12]);
    console.log('PASS read cursor, ordering and duplicate suppression');

    h.setHandler(async()=>{throw new Error('network');});
    h.ids.chatInputMessage.value='preserved';
    await h.ids.chatForm.listeners.submit({preventDefault(){}});
    assert.equal(h.ids.chatInputMessage.value,'preserved');
    assert.match(h.ids.chatSendStatus.textContent,/giữ lại/);
    assert.equal(h.ids.btnSendChat.disabled,false);
    console.log('PASS failed send retains draft and is not auto-replayed');

    let release;
    h.setHandler(()=>new Promise(resolve=>release=resolve));
    const before=h.calls.length;
    h.events.online(); h.events.online();
    assert.equal(h.calls.length,before+1);
    release(response({ok:true,workspace_id:'test-ws',messages:[]})); await tick();
    console.log('PASS only one polling request in flight');
    h.document.hidden=true; const hiddenCalls=h.calls.length; h.events.online();
    assert.equal(h.calls.length,hiddenCalls); h.document.hidden=false;
    h.setHandler(async()=>({status:403,ok:false})); h.events.online(); await tick();
    assert.equal(h.ids.btnSendChat.disabled,true);
    const denied=h.calls.length; h.events.online(); assert.equal(h.calls.length,denied);
    console.log('PASS hidden tab pause and access revocation stop');

    const b=harness('internal_bulletins.js'); await tick();
    b.setHandler(async()=>response({status:'success',workspace_id:'test-ws',bulletins:[{id:1,title:'<script>literal</script>',content:'body',author_name:'manager',priority:'NORMAL',priority_label:'Thông báo',created_at:'2026-10-09T00:00:00Z'}]}));
    b.events.online(); await tick();
    const card=b.ids.bulletinLiveFeed.children[0].children[0];
    assert.equal(card.children[1].textContent,'<script>literal</script>');
    assert.equal(card.children[3].children.length,2, 'Employee cannot see edit link');
    const old=b.ids.bulletinLiveFeed.children[0];
    b.setHandler(async()=>{throw new Error('network');}); b.events.online(); await tick();
    assert.equal(b.ids.bulletinLiveFeed.children[0],old);
    console.log('PASS bulletin escaping, employee controls and retained feed on failure');
}
run().catch(error=>{console.error(error);process.exitCode=1;});
