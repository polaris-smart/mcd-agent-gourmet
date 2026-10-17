/* Optional DOM interaction check: provide jsdom via NODE_PATH; no browser/layout claim. */
const {JSDOM}=require('jsdom');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
function open(saved){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'docs/index.html'),'utf8'),{url:'https://example.test/',runScripts:'outside-only'});
 const w=dom.window;let clipboard='';
 w.matchMedia=()=>({matches:true});w.HTMLElement.prototype.scrollIntoView=()=>{};
 Object.defineProperty(w.navigator,'clipboard',{value:{writeText:async text=>{clipboard=text;}}});
 if(saved)w.localStorage.setItem('gourmet.preferences.v1',saved);
 for(const name of ['data.js','review.js','app.js'])w.eval(fs.readFileSync(path.join(root,'docs',name),'utf8'));
 const get=id=>w.document.getElementById(id);
 const change=(id,value,event='input')=>{get(id).value=value;get(id).dispatchEvent(new w.Event(event,{bubbles:true}));};
 return {dom,w,get,change,clipboard:()=>clipboard};
}
(async()=>{
 const x=open(),{w,get,change}=x;
 assert.match(get('store-name').textContent,/已脱敏/);
 assert.equal(get('sample').options.length,w.GOURMET_SNAPSHOTS.length);
 assert.equal(get('taste').value,'any');assert.equal(get('controls').elements.namedItem('sugar').value,'any');
 assert.equal(get('nutrition-options').open,false);
 const ids=[...w.document.querySelectorAll('[id]')].map(e=>e.id);assert.equal(new Set(ids).size,ids.length);
 for(const label of w.document.querySelectorAll('label[for]'))assert.ok(get(label.htmlFor),'Missing label target '+label.htmlFor);
 w.document.querySelector('[name=sugar][value=regular]').click();
 assert.equal(get('plans').children.length,2);
 assert.ok([...get('plans').children].every(row=>!row.textContent.includes('无糖可口可乐')));
 change('ice','none');change('handoff-location','南京市江宁区');
 get('copy-prompt').click();await Promise.resolve();
 assert.match(x.clipboard(),/有糖可乐（必须满足）/);assert.match(x.clipboard(),/南京市江宁区/);assert.match(x.clipboard(),/去冰/);
 get('plans').querySelector('[data-select]').click();assert.equal(get('receipt').hidden,false);
 get('copy').click();await Promise.resolve();assert.match(x.clipboard(),/已脱敏|历史快照/);assert.match(x.clipboard(),/历史快照/);
 const old=1;
 change('sample',String(old),'change');assert.equal(get('receipt').hidden,true);assert.match(get('store-address').textContent,/已脱敏/);
 assert.match(get('ice-note').textContent,/未核验/);assert.equal(get('empty-message').hidden,false);
 assert.equal(get('plans').querySelectorAll('[data-select]:not(:disabled)').length,0);
 change('sodium','987');get('remember').click();
 const saved=w.localStorage.getItem('gourmet.preferences.v1');assert.equal(JSON.parse(saved).sodium_limit,987);
 const restored=open(saved);assert.equal(restored.get('sodium').value,'987');assert.equal(restored.get('nutrition-options').open,true);restored.dom.window.close();
 change('budget','');const before=x.clipboard();get('copy-prompt').click();await Promise.resolve();
 assert.equal(x.clipboard(),before);assert.equal(get('plans').children.length,0);
 get('reset').click();assert.equal(get('sodium').value,'');assert.equal(get('taste').value,'any');assert.equal(get('controls').elements.namedItem('sugar').value,'any');
 x.dom.window.close();console.log('DOM flows passed: defaults, regular cola, quote copy, store switch, unknown ice, custom sodium restore, invalid input, reset. No visual/layout verification.');
})().catch(e=>{console.error(e);process.exitCode=1;});
