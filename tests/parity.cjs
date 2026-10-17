const fs=require('node:fs'),cp=require('node:child_process'),assert=require('node:assert/strict');
const {evaluate,defaultPick,pickReason,orderCard}=require('../docs/review.js');
const files=JSON.parse(fs.readFileSync('fixtures/demo-snapshots.json','utf8')).map(name=>'fixtures/'+name);
const cases=[];for(const budget of [1,30,32,32.5,33.5,35,50])for(const taste of ['any','spicy','no-spicy'])for(const sodium of [null,800,1200,1500])for(const side of ['any','fries'])for(const sugar of ['any','zero','regular'])for(const energy_limit of [null,600])for(const protein_min of [null,25])for(const ice of ['any','none','less'])cases.push({ice,budget_cents:Math.round(budget*100),taste,sodium_limit:sodium,side,sugar,energy_limit,protein_min});
const script=`import sys,json
from gourmet.core import review, default_pick, pick_reason, order_card
d=json.load(open(sys.argv[1]))
bid=d.get('baseline_plan_id')
out=[]
for q in json.load(sys.stdin):
    q=dict(q)
    if bid: q['baseline_plan_id']=bid
    r=review(d,**q)
    pick=default_pick(r)
    out.append({**{k:r[k] for k in ['reviewers','feasible_count','disagreement','tradeoffs','next_step','baseline','best_saving']},
        'plans':[[p['id'],p['eligible'],p['reasons']] for p in r['plans']],
        'default_pick': None if pick is None else pick['id'],
        'pick_reason': None if pick is None else pick_reason(r,pick['id']),
        'order_card': None if pick is None else order_card(r,pick['id'])})
print(json.dumps(out))`;
for(const file of files){
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const py=cp.spawnSync(process.env.PYTHON||'python3',['-B','-c',script,file],{input:JSON.stringify(cases),encoding:'utf8',maxBuffer:64*1024*1024});assert.equal(py.status,0,py.stderr);const results=JSON.parse(py.stdout);
cases.forEach((req,i)=>{
 const js=evaluate(data,req),p=results[i];
 for(const key of ['reviewers','feasible_count','disagreement','tradeoffs','next_step','baseline','best_saving'])assert.deepEqual(js[key],p[key],key+' @ '+file);
 assert.deepEqual(js.plans.map(x=>[x.id,x.eligible,x.reasons]),p.plans);
 const pick=defaultPick(js);
 assert.deepEqual(pick?pick.id:null,p.default_pick,'default_pick @ '+file);
 assert.deepEqual(pick?pickReason(js,pick.id):null,p.pick_reason,'pick_reason @ '+file);
 assert.deepEqual(pick?orderCard(js,pick.id):null,p.order_card,'order_card @ '+file);
});}
console.log(`Python/JS parity passed: ${cases.length*files.length} scenarios across ${files.length} snapshots (含 baseline / default_pick / pick_reason / order_card)`);
