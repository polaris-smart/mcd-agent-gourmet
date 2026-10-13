'use strict';
const $=id=>document.getElementById(id);let data=window.GOURMET_DATA;
const names={budget:'预算师',nutrition:'营养观察员',taste:'口味师'};
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=c=>(c/100).toFixed(2);let result,selected=null;
function itemName(i){return i.name+(i.customizations?.length?'（'+i.customizations.join('、')+'）':'');}
function requirements(){return {budget_cents:Math.round(Number($('budget').value)*100),taste:$('taste').value,sodium_limit:$('sodium').value?Number($('sodium').value):null,side:$('fries').checked?'fries':'any',sugar:$('controls').elements.namedItem('sugar').value,ice:$('ice').value,energy_limit:$('energy').value?Number($('energy').value):null,protein_min:$('protein').value?Number($('protein').value):null};}
function render(){
 const hadSelection=selected!==null;selected=null;$('receipt').hidden=true;
 $('selection-message').textContent=hadSelection?'条件已改变，之前的选择已清除。请重新确认餐单。':'';
 const valid=$('controls').checkValidity();$('budget-error').textContent=valid?'':'请检查预算（1～10000 元、最多两位小数）和营养条件（正整数或留空）。';
 if(!valid){$('plans').replaceChildren();$('voices').replaceChildren();$('tradeoffs').replaceChildren();$('result-summary').textContent='先填一个有效预算';$('consensus').textContent='';$('empty-message').hidden=true;result=null;return;}
 result=GourmetReview.evaluate(data,requirements());
 const picks=result.tradeoffs[$('strategy').value].map(id=>result.plans.find(p=>p.id===id));
 $('tradeoffs').innerHTML=picks.length?picks.map(p=>`<p><strong>${escape(p.name)} · ${escape(p.variant)}</strong><br>¥${money(p.price_cents)} · 钠 ${p.sodium_mg} mg · ${p.energy_kcal??'未知'} kcal · 蛋白质 ${p.protein_g??'未知'} g${result.requirements.taste==='spicy'?' · '+(p.taste_match?'保留辣味偏好':'无辣味，供取舍'):''}</p>`).join(''):'<p>当前没有满足条件且钠数据完整的取舍候选。</p>';
 document.querySelectorAll('[data-budget]').forEach(b=>b.setAttribute('aria-pressed',Number(b.dataset.budget)*100===result.requirements.budget_cents?'true':'false'));
 $('result-summary').textContent=`${data.plans.length} 份完整餐单 · ${result.feasible_count} 份符合当前硬性条件`;
 $('empty-message').hidden=!!result.feasible_count;
 $('empty-message').textContent=result.next_step;
 $('consensus').textContent=!result.feasible_count?'这次先不勉强。没有合适的，就明确说没有。':result.disagreement?'意见不一致，也没关系。把取舍留给你。':'这次意见一致。你仍然可以比较后再选。';
 $('voices').innerHTML=Object.entries(names).map(([role,name])=>{const p=result.plans.find(x=>x.id===result.reviewers[role]);const desc=!p?'没有符合条件且数据足够的餐单':role==='budget'?`当次核价 ¥${money(p.price_cents)}，在可选餐单中价格较低。`:role==='nutrition'?`钠 ${p.sodium_mg} mg，在可选且数据完整的餐单中较少。`:result.requirements.taste==='spicy'&&!p.spicy?'没有满足其他条件的辣味餐单；这个是备选。':result.requirements.taste==='spicy'?'这份保留了你想吃的辣味。':'这份符合口味条件，同等情况下先看价格。';return `<div class="voice"><span class="avatar" aria-hidden="true">${role==='budget'?'省':role==='nutrition'?'知':'味'}</span><div><h3>${name}</h3><p>${p?escape(p.name):'先不推荐'}</p><small>${p?escape(p.variant)+' · ':''}${escape(desc)}</small></div></div>`}).join('');
 $('plans').innerHTML=result.plans.map(p=>{let tags=Object.entries(result.reviewers).filter(([,id])=>id===p.id).map(([role])=>`<span class="role-tag">${names[role]}选择</span>`).join('');let note=p.reasons.join('；')||(result.requirements.taste==='spicy'&&!p.spicy?'符合硬性条件，但没有辣味。':'符合硬性条件。'+(p.spicy?'保留辣味。':'非辣味模板。'));if(p.sodium_mg==null)note+=' 营养数据不完整。';return `<tr class="${p.eligible?'':'blocked'}" data-plan="${p.id}"><td><span class="meal-title">${escape(p.name)}</span><span class="meal-items">${p.items.map(i=>escape(itemName(i))).join(' + ')}</span>${tags}</td><td><span class="price">¥${money(p.price_cents)}</span><span class="remaining">${p.remaining_cents>=0?'余量 ¥'+money(p.remaining_cents):'超出 ¥'+money(-p.remaining_cents)}</span></td><td class="nutrients">${p.sodium_mg==null?'钠未知':p.sodium_mg+' mg 钠'}<small>${p.energy_kcal==null?'能量未知':p.energy_kcal+' kcal'} · ${p.protein_g==null?'蛋白质未知':p.protein_g+' g 蛋白质'}</small></td><td class="tradeoff">${escape(note)}</td><td><button type="button" class="choose" data-select="${p.id}" aria-pressed="false" aria-label="选择 ${escape(p.name+' '+p.variant)}" ${p.eligible?'':'disabled'}>${p.eligible?'选这份':'不符合条件'}</button></td></tr>`}).join('');
}
$('strategy').addEventListener('change',render);
$('remember').addEventListener('click',()=>{if(!$('controls').checkValidity())return;try{localStorage.setItem('gourmet.preferences.v1',JSON.stringify(requirements()));$('preference-message').textContent='已保存在这个浏览器。只记条件，不保存账号、位置或餐单选择。';}catch{$('preference-message').textContent='浏览器未允许保存；本次仍可正常使用。';}});
$('forget').addEventListener('click',()=>{try{localStorage.removeItem('gourmet.preferences.v1');$('preference-message').textContent='已清除保存的条件。';}catch{$('preference-message').textContent='浏览器未允许访问保存区。';}});
$('copy-prompt').addEventListener('click',async()=>{const q=requirements();if(!$('controls').checkValidity())return;
const text=`请用麦门点餐议事会帮我选一顿完整的麦当劳：预算 ${money(q.budget_cents)} 元，主食、小食、饮料各一份。口味：${$('taste').selectedOptions[0].text}；饮料：${{regular:'有糖可乐（必须满足）',zero:'无糖可乐（必须满足）',any:'有糖或无糖可乐都可以'}[q.sugar]}；冰量：${$('ice').selectedOptions[0].text}；${q.side==='fries'?'必须有薯条。':''}${q.sodium_limit?'钠上限 '+q.sodium_limit+' mg。':''}${q.energy_limit?'能量上限 '+q.energy_limit+' kcal。':''}${q.protein_min?'蛋白质至少 '+q.protein_min+' g。':''}
使用方式：${$('handoff-channel').selectedOptions[0].text}。先确认位置或配送地址，让我选择门店；按当前菜单和官方特调重新核价，最多比较 12 份。若我想用券或积分，请区分兑换与本次渠道适用性。未知条件请说清，不要自动放宽。只查询，不领券、不兑换、不下单。`;
$('workbuddy-prompt').textContent=text;try{await navigator.clipboard.writeText(text);$('prompt-message').textContent='已复制，粘贴到安装本 Skill 的 WorkBuddy 对话即可。';}catch{$('prompt-message').textContent='请手动选择并复制上方文字。';}});
try{const saved=JSON.parse(localStorage.getItem('gourmet.preferences.v1')||'null');if(saved&&typeof saved==='object'){
 if(Number.isInteger(saved.budget_cents)&&saved.budget_cents>=100&&saved.budget_cents<=1000000)$('budget').value=saved.budget_cents/100;
 if(['any','spicy','no-spicy'].includes(saved.taste))$('taste').value=saved.taste;
 if(['any','standard','less','none','extra'].includes(saved.ice))$('ice').value=saved.ice;
 if(['any','regular','zero'].includes(saved.sugar))$('controls').elements.namedItem('sugar').value=saved.sugar;
 if([null,800,1200,1500].includes(saved.sodium_limit))$('sodium').value=saved.sodium_limit??'';
 for(const [id,key] of [['energy','energy_limit'],['protein','protein_min']])if(Number.isInteger(saved[key])&&saved[key]>0)$(id).value=saved[key];
 $('fries').checked=saved.side==='fries';$('preference-message').textContent='已载入你在这个浏览器保存的条件，可随时清除。';
}}catch{/* Storage is optional. */}

$('controls').addEventListener('submit',e=>e.preventDefault());$('controls').addEventListener('input',render);
$('controls').addEventListener('click',e=>{const b=e.target.closest('[data-budget]');if(b){$('budget').value=b.dataset.budget;render();}});
$('reset').addEventListener('click',()=>{$('controls').reset();render();});
$('plans').addEventListener('click',e=>{const b=e.target.closest('[data-select]');if(!b||b.disabled||!result)return;selected=result.plans.find(p=>p.id===b.dataset.select&&p.eligible);if(!selected)return;document.querySelectorAll('[data-select]').forEach(x=>{const active=x.dataset.select===selected.id;x.setAttribute('aria-pressed',String(active));x.textContent=x.disabled?'不符合条件':active?'已选择 ✓':'选这份';x.closest('tr').classList.toggle('is-selected',active);});$('receipt').hidden=false;$('chosen').textContent=selected.items.map(itemName).join(' + ')+` · 当次整单核价 ¥${money(selected.price_cents)}`;$('selection-message').textContent='已记录你的选择，未创建订单或支付。';$('receipt').focus({preventScroll:true});$('receipt').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'nearest'});});
$('copy').addEventListener('click',async()=>{if(!selected)return;const text=`麦门点餐议事会｜历史快照演示，非当前报价\n${data.store.name}\n核价时间：${data.captured_at}\n${selected.items.map(itemName).join(' + ')}\n当次整单核价：¥${money(selected.price_cents)}\n钠：${selected.sodium_mg??'未知'} mg；能量：${selected.energy_kcal??'未知'} kcal\n已选餐单，未下单。当前购买须在官方渠道重新核价。\nhttps://polaris-smart.github.io/mcd-agent-gourmet/`;try{await navigator.clipboard.writeText(text);$('selection-message').textContent='餐单已复制，包含历史快照与未下单说明。';}catch{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));a.download='麦门餐单-历史快照.txt';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);$('selection-message').textContent='浏览器未允许复制，已下载餐单文本。';}});
function renderSource(){
 $('data-notice').textContent='当前为历史快照演示，非实时价格。'+data.store.name+' · '+new Date(data.captured_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})+'（北京时间）。实时核价请使用 WorkBuddy 或本机 CLI。';
 $('source').textContent=`${data.store.name} · ${new Date(data.captured_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})}（北京时间）核价 · 不含用券优惠`;
}
$('sample').addEventListener('change',()=>{data=window.GOURMET_SNAPSHOTS[Number($('sample').value)];renderSource();render();});
renderSource();
render();
