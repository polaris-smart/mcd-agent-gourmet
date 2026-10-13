const fs=require('node:fs'),cp=require('node:child_process'),assert=require('node:assert/strict');
const {evaluate}=require('../docs/review.js');const files=['fixtures/snapshot.json','fixtures/customized-snapshot.json'];
const cases=[];for(const budget of [1,30,32,32.5,33.5,35,50])for(const taste of ['any','spicy','no-spicy'])for(const sodium of [null,800,1200,1500])for(const side of ['any','fries'])for(const sugar of ['any','zero','regular'])for(const energy_limit of [null,600])for(const protein_min of [null,25])for(const ice of ['any','none','less'])cases.push({ice,budget_cents:Math.round(budget*100),taste,sodium_limit:sodium,side,sugar,energy_limit,protein_min});
for(const file of files){
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const script=`import sys,json
from gourmet.core import review
d=json.load(open(sys.argv[1]))
results=[]
for q in json.load(sys.stdin):
 r=review(d,**q)
 results.append({**{k:r[k] for k in ['reviewers','feasible_count','disagreement','tradeoffs','next_step']},'plans':[[p['id'],p['eligible'],p['reasons']] for p in r['plans']]})
print(json.dumps(results))`;
const py=cp.spawnSync(process.env.PYTHON||'python3',['-B','-c',script,file],{input:JSON.stringify(cases),encoding:'utf8',maxBuffer:32*1024*1024});assert.equal(py.status,0,py.stderr);const results=JSON.parse(py.stdout);
cases.forEach((req,i)=>{const js=evaluate(data,req),p=results[i];for(const key of ['reviewers','feasible_count','disagreement','tradeoffs','next_step'])assert.deepEqual(js[key],p[key]);assert.deepEqual(js.plans.map(x=>[x.id,x.eligible,x.reasons]),p.plans);});
}
console.log(`Python/JS parity passed: ${cases.length*files.length} scenarios across ${files.length} snapshots`);
