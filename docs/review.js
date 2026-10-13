/* Same decision contract as gourmet/core.py; cross-runtime parity is tested. */
(function(root){
'use strict';
function evaluate(data, req){
 const {budget_cents:budget,taste,sodium_limit:limit,side}=req;
 const plans=data.plans.map(original=>{
  const p={...original},reasons=[];
  if(['main','side','drink'].some(kind=>p.items.filter(i=>i.kind===kind).reduce((s,i)=>s+i.quantity,0)<1)) reasons.push('不满足主食＋小食＋饮料各至少一份');
  if(p.price_cents>budget)reasons.push('超预算 ¥'+((p.price_cents-budget)/100).toFixed(2));
  if(taste==='no-spicy'&&p.spicy!==false)reasons.push('含辣或辣味信息未确认');
  if(side==='fries'&&!p.items.some(i=>i.kind==='side'&&i.is_fries))reasons.push('小食不含薯条');
  if(limit!==null){if(p.sodium_mg==null)reasons.push('钠数据不完整，无法核验上限');else if(p.sodium_mg>limit)reasons.push('超过你设定的钠上限 '+limit+' mg');}
  return {...p,reasons,eligible:!reasons.length,remaining_cents:budget-p.price_cents,taste_match:taste!=='spicy'||p.spicy===true};
 });
 const feasible=plans.filter(p=>p.eligible),byId=(a,b)=>a.id<b.id?-1:a.id>b.id?1:0;
 const cheapest=(a,b)=>a.price_cents-b.price_cents||byId(a,b);
 const budgetPick=[...feasible].sort(cheapest)[0];
 const nutritionPick=feasible.filter(p=>p.sodium_mg!=null).sort((a,b)=>a.sodium_mg-b.sodium_mg||cheapest(a,b))[0];
 const tastePick=[...feasible].sort((a,b)=>Number(!a.taste_match)-Number(!b.taste_match)||cheapest(a,b))[0];
 const reviewers={budget:budgetPick?.id??null,nutrition:nutritionPick?.id??null,taste:tastePick?.id??null};
 const known=feasible.filter(p=>p.sodium_mg!=null),tradeoffs={};
 for(const [name,dimensions] of Object.entries({price_sodium:p=>[p.price_cents,p.sodium_mg],taste_sodium:p=>[Number(!p.taste_match),p.sodium_mg]})){
  tradeoffs[name]=known.filter(p=>!known.some(q=>{const a=dimensions(p),b=dimensions(q);return b.every((v,i)=>v<=a[i])&&b.some((v,i)=>v<a[i]);})).sort(cheapest).map(p=>p.id);
 }
 return {tradeoffs,plans,reviewers,feasible_count:feasible.length,disagreement:new Set(Object.values(reviewers).filter(Boolean)).size>1,requirements:req};
}
if(typeof module!=='undefined'&&module.exports)module.exports={evaluate};else root.GourmetReview={evaluate};
})(typeof window!=='undefined'?window:globalThis);
