const fs=require('node:fs'),cp=require('node:child_process'),assert=require('node:assert/strict');
const {evaluate}=require('../docs/review.js');const data=JSON.parse(fs.readFileSync('fixtures/snapshot.json','utf8'));
const cases=[];for(const budget of [1,30,32,32.5,33.5,35,50])for(const taste of ['any','spicy','no-spicy'])for(const sodium of [null,800,1200,1500])for(const side of ['any','fries'])cases.push({budget_cents:Math.round(budget*100),taste,sodium_limit:sodium,side});
const script=`import sys,json\nfrom gourmet.core import review\nd=json.load(open('fixtures/snapshot.json'))\nprint(json.dumps([review(d,**q) for q in json.load(sys.stdin)]))`;
const py=cp.spawnSync(process.env.PYTHON||'python3',['-B','-c',script],{input:JSON.stringify(cases),encoding:'utf8'});assert.equal(py.status,0,py.stderr);const results=JSON.parse(py.stdout);
cases.forEach((req,i)=>{const js=evaluate(data,req),p=results[i];for(const key of ['reviewers','feasible_count','disagreement','tradeoffs'])assert.deepEqual(js[key],p[key]);assert.deepEqual(js.plans.map(x=>[x.id,x.eligible,x.reasons]),p.plans.map(x=>[x.id,x.eligible,x.reasons]));});console.log(`Python/JS parity passed: ${cases.length} scenarios`);
