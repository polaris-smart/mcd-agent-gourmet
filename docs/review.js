/* Same decision contract as gourmet/core.py; cross-runtime parity is tested. */
(function(root){
'use strict';
const byId=(a,b)=>a.id<b.id?-1:a.id>b.id?1:0;
const money=c=>(c/100).toFixed(2);
const num=v=>String(Number(v));
function evaluate(data,req){
 const {budget_cents:budget,taste,sodium_limit:limit,side,sugar='any',energy_limit:energy=null,protein_min:protein=null,ice='any'}=req;
 const plans=data.plans.map(original=>{
  const p={...original},reasons=[];
  if(['main','side','drink'].some(kind=>p.items.filter(i=>i.kind===kind).reduce((s,i)=>s+i.quantity,0)<1)) reasons.push('不满足主食＋小食＋饮料各至少一份');
  if(budget!=null&&p.price_cents>budget)reasons.push('超预算 ¥'+((p.price_cents-budget)/100).toFixed(2));
  if(taste==='no-spicy'&&p.spicy!==false)reasons.push('含辣或辣味信息未确认');
  if(side==='fries'&&!p.items.some(i=>i.kind==='side'&&i.is_fries))reasons.push('小食不含薯条');
  if(ice!=='any'&&p.items.some(i=>i.kind==='drink'&&i.ice!==ice))reasons.push('冰量未核验为所选条件；请实时特调核价');
  if(sugar!=='any'&&p.items.some(i=>i.kind==='drink'&&i.sugar!==sugar))reasons.push('饮料含糖类型不符或未确认');
  for(const [key,threshold,label,upper] of [['energy_kcal',energy,'能量',true],['protein_g',protein,'蛋白质',false]]){
   if(threshold!==null){if(p[key]==null)reasons.push(label+'数据不完整，无法核验条件');else if(upper?p[key]>threshold:p[key]<threshold)reasons.push(upper?'超过你设定的能量上限 '+threshold+' kcal':'低于你设定的蛋白质下限 '+threshold+' g');}
  }
  if(limit!==null){if(p.sodium_mg==null)reasons.push('钠数据不完整，无法核验上限');else if(p.sodium_mg>limit)reasons.push('超过你设定的钠上限 '+limit+' mg');}
  return {...p,reasons,eligible:!reasons.length,remaining_cents:budget==null?null:budget-p.price_cents,taste_match:taste!=='spicy'||p.spicy===true};
 });
 let baseline=null;
 const baselineId=req.baseline_plan_id!=null?req.baseline_plan_id:(data.baseline_plan_id!=null?data.baseline_plan_id:null);
 if(baselineId!=null){
  const src=plans.find(p=>p.id===baselineId);
  if(src)baseline={kind:'plan',plan_id:src.id,price_cents:src.price_cents,label:src.name,store_code:data.store.code};
 }
 if(baseline)for(const p of plans){p.saving_cents=baseline.price_cents-p.price_cents;p.saving_percent=Math.round(1000*p.saving_cents/baseline.price_cents)/10;}
 const feasible=plans.filter(p=>p.eligible);
 const cheapest=(a,b)=>a.price_cents-b.price_cents||byId(a,b);
 const budgetPick=[...feasible].sort(cheapest)[0];
 const nutritionPick=feasible.filter(p=>p.sodium_mg!=null).sort((a,b)=>a.sodium_mg-b.sodium_mg||cheapest(a,b))[0];
 const tastePick=[...feasible].sort((a,b)=>Number(!a.taste_match)-Number(!b.taste_match)||cheapest(a,b))[0];
 const reviewers={budget:budgetPick?.id??null,nutrition:nutritionPick?.id??null,taste:tastePick?.id??null};
 const known=feasible.filter(p=>p.sodium_mg!=null),tradeoffs={};
 for(const [name,dimensions] of Object.entries({price_sodium:p=>[p.price_cents,p.sodium_mg],taste_sodium:p=>[Number(!p.taste_match),p.sodium_mg]})){
  tradeoffs[name]=known.filter(p=>!known.some(q=>{const a=dimensions(p),b=dimensions(q);return b.every((v,i)=>v<=a[i])&&b.some((v,i)=>v<a[i]);})).sort(cheapest).map(p=>p.id);
 }
 const complete=known.filter(p=>p.energy_kcal!=null&&p.protein_g!=null),dims=p=>[p.price_cents,p.sodium_mg,p.energy_kcal,-p.protein_g];
 tradeoffs.nutrition_multi=complete.filter(p=>!complete.some(q=>{const a=dims(p),b=dims(q);return b.every((v,i)=>v<=a[i])&&b.some((v,i)=>v<a[i]);})).sort(cheapest).map(p=>p.id);
 const enough=plans.filter(p=>p.reasons.every(r=>r.startsWith('超预算')));
 const next_step=feasible.length?(budget==null?'未设预算：以上候选都符合其他硬性条件，请比较后选择。':'可选餐单均已列出，请比较后选择。'):enough.length?'保持其他条件不变，候选中最低需要 ¥'+(Math.min(...enough.map(p=>p.price_cents))/100).toFixed(2)+'；是否增加预算由你决定。':'当前候选没有满足其他条件的餐单。可在所选门店扩展组合，或由你修改偏好；不会自动放宽条件。';
 let bestSaving=null;
 if(baseline){
  const winners=feasible.filter(p=>p.saving_cents>0).sort((a,b)=>b.saving_cents-a.saving_cents||a.price_cents-b.price_cents||byId(a,b));
  if(winners[0])bestSaving={plan_id:winners[0].id,saving_cents:winners[0].saving_cents,saving_percent:winners[0].saving_percent};
 }
 const requirements={...req,people:req.people??1,budget_scope:req.budget_scope??'total'};
 return {next_step,tradeoffs,plans,baseline,best_saving:bestSaving,reviewers,feasible_count:feasible.length,disagreement:new Set(Object.values(reviewers).filter(Boolean)).size>1,requirements,store:data.store,mode:data.mode,captured_at:data.captured_at};
}
function defaultPick(result){
 const eligible=result.plans.filter(p=>p.eligible);
 if(!eligible.length)return null;
 const list=[...eligible];
 if(result.baseline)list.sort((a,b)=>(b.saving_cents||0)-(a.saving_cents||0)||a.price_cents-b.price_cents||byId(a,b));
 else list.sort((a,b)=>a.price_cents-b.price_cents||byId(a,b));
 return list[0];
}
function pickReason(result,planId){
 const plan=result.plans.find(p=>p.id===planId);
 if(!plan||!plan.eligible)throw new Error('只能为符合条件的候选给理由。');
 const eligible=result.plans.filter(p=>p.eligible);
 if(result.baseline&&plan.saving_cents>0)return `比「${result.baseline.label}」省 ¥${money(plan.saving_cents)}（${plan.saving_percent.toFixed(1)}%）`;
 const cheapest=[...eligible].sort((a,b)=>a.price_cents-b.price_cents||byId(a,b))[0];
 if(cheapest.id===plan.id)return `在满足条件的 ${eligible.length} 份候选里价格最低（¥${money(plan.price_cents)}）`;
 const known=eligible.filter(p=>p.sodium_mg!=null);
 if(known.length){
  const lowest=[...known].sort((a,b)=>a.sodium_mg-b.sodium_mg||a.price_cents-b.price_cents||byId(a,b))[0];
  if(lowest.id===plan.id)return `在钠数据完整的候选里钠最低（${num(plan.sodium_mg)} mg）`;
 }
 return '符合你的全部硬性条件';
}
function orderCard(result,planId){
 const picked=planId==null?defaultPick(result):result.plans.find(p=>p.id===planId);
 if(!picked)throw new Error('没有符合条件的候选，无法生成点单卡。');
 if(!picked.eligible)throw new Error('该候选不符合当前条件，不能生成点单卡。');
 const ways=Array.isArray(picked.take_way_options)?picked.take_way_options:[];
 const way=ways.length&&ways[0]&&ways[0].title?ways[0].title:'到店自取';
 const lines=[`门店：${result.store.name}（${result.store.code}）· ${way}`];
 picked.items.forEach((item,index)=>{const spec=(item.customizations||[]).join('、');lines.push(`${index+1}. ${item.name}${spec?'（'+spec+'）':''}`);});
 lines.push(`合计：¥${money(picked.price_cents)}`);
 if(result.baseline&&picked.saving_cents>0)lines.push(`比「${result.baseline.label}」省 ¥${money(picked.saving_cents)}（${picked.saving_percent.toFixed(1)}%）`);
 const people=result.requirements.people||1;
 if(people>1)lines.push(`${people} 人；人均 ¥${money(Math.ceil(picked.price_cents/people))}`);
 if(picked.display_price_note)lines.push(`价格说明：${picked.display_price_note}`);
 lines.push('以上只是记录你的选择；没有下单、没有支付。');
 return {plan_id:picked.id,title:picked.name,variant:picked.variant,lines,text:lines.join('\n'),total_cents:picked.price_cents,status:'selected_not_ordered'};
}
if(typeof module!=='undefined'&&module.exports)module.exports={evaluate,defaultPick,pickReason,orderCard};else root.GourmetReview={evaluate,defaultPick,pickReason,orderCard};
})(typeof window!=='undefined'?window:globalThis);
