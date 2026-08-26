from pathlib import Path
import json,re

ROOT=Path('.')

def sub1(text, pattern, repl, label, flags=re.S):
    out,n=re.subn(pattern,repl,text,count=1,flags=flags)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 replacement, got {n}')
    return out

# ---- rules ----
p=ROOT/'data/rules.json'
r=json.loads(p.read_text())
r['format_version']=3
r['data_version']='2026-08-26-ranges-v3'
r['premium_time']['editable']=True
r['twitter_bonus']={
    'key':'twitter_last_time','trusted_time_keys':['last_net_time','last_inner_time'],
    'refresh_on_export':True,'duration_seconds':604800,
    'note':'書出し時にセーブ内の信頼済み時刻へ更新する。未来時刻は生成しない。'
}
r['abnormal_flag']={
    'flag':'8d84d86dd','paired_flag':'86dd8d84d','flags_key':'flags',
    'triggers':[
      {'field':'rabbit','op':'>','value':999,'confidence':'confirmed'},
      {'field':'adon_exp','op':'>=','value':10,'confidence':'confirmed'},
      {'field':'adon_gp','op':'>=','value':10,'confidence':'confirmed'},
      {'field':'adon_rare','op':'>=','value':10,'confidence':'confirmed'},
      {'field':'adon_time','op':'>=','value':10,'confidence':'confirmed'}
    ]
}
p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')

# ---- append confirmed magic-creature material IDs ----
p=ROOT/'data/items.tsv'
t=p.read_text()
magic=json.loads((ROOT/'data/magic_creatures.json').read_text())
existing={line.split('\t',1)[0] for line in t.splitlines()[1:] if line.strip()}
rows=[]
for x in magic['items']:
    if x.get('inferred') or x['base_id'] in existing: continue
    rows.append('\t'.join([x['base_id'],x['name'],'18','MagicCreature','confirmed','ipa-v5.10-static','5.10','selectable']))
if rows:
    t=t.rstrip('\n')+'\n'+'\n'.join(rows)+'\n'
p.write_text(t)

# ---- Wiki order + inferred Omega ----
p=ROOT/'data/wiki_items.json'
w=json.loads(p.read_text())
w.setdefault('ordered',{}).setdefault('18',{})['魔造生物']=[x['name'] for x in magic['items']]
w.setdefault('unresolved_meta',{})['オメガ']={
    'category_id':18,'group':'魔造生物','id_guess':'8538','guess':'high',
    'effect':'内部IDは高確度推定。v5.10の魔造生物IDが8501～8537で連続し、現行Wikiではオメガが後続追加。'
}
p.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n')

# ---- model.js ----
p=ROOT/'js/model.js'
m=p.read_text()
new_premium=r'''function parsePremiumTime(){
  if(!state.entries.has('premiumTimePoint'))return null;const s=String(get('premiumTimePoint')),r=state.rules?.premium_time||{};
  if(!/^\d{24}$/.test(s))return{valid:false,raw:s,values:[],total:null};const values=[...s].map(Number),valid=values.every(v=>v>=(r.hour_min??0)&&v<=(r.hour_max??3)),total=values.reduce((a,b)=>a+b,0);return{valid:valid&&total<=(r.total_max??32),raw:s,values,total};
}
function setPremiumTime(values){
  const r=state.rules?.premium_time||{},vals=Array.from(values||[],Number);if(vals.length!==(r.hours??24))throw Error('Premium Timeは24時間分必要です');
  if(vals.some(v=>!Number.isInteger(v)||v<(r.hour_min??0)||v>(r.hour_max??3)))throw Error('Premium Timeは各時間0～3です');
  const total=vals.reduce((a,b)=>a+b,0);if(total>(r.total_max??32))throw Error(`Premium Time合計は${r.total_max??32}以下です`);
  const s=vals.join('');setScalar(r.key||'premiumTimePoint',s);const mirror=r.mirror_key||'premiumTimePoint_appo';if(state.entries.has(mirror))setScalar(mirror,s);return{values:vals,total,raw:s,valid:true};
}
function refreshTwitterBonus(){
  const tr=state.rules?.twitter_bonus||{},key=tr.key||'twitter_last_time';if(!state.entries.has(key))return null;
  let trusted=0,source=null;for(const k of (tr.trusted_time_keys||['last_net_time','last_inner_time']))if(state.entries.has(k)){const v=Number(get(k));if(Number.isSafeInteger(v)&&v>trusted){trusted=v;source=k;}}
  if(!trusted)return null;setScalar(key,trusted);return{time:trusted,source};
}
function abnormalFlagReport(){
  const r=state.rules?.abnormal_flag||{},hits=[];for(const t of (r.triggers||[])){if(!state.entries.has(t.field))continue;const v=Number(get(t.field));let hit=false;if(t.op==='>')hit=v>t.value;else if(t.op==='>=')hit=v>=t.value;else if(t.op==='<')hit=v<t.value;else if(t.op==='<=')hit=v<=t.value;if(hit)hits.push({...t,current:v});}
  let flags=[];if(state.entries.has(r.flags_key||'flags')){const v=get(r.flags_key||'flags');if(Array.isArray(v))flags=v.map(String);}
  return{flag:r.flag||'8d84d86dd',paired_flag:r.paired_flag||'86dd8d84d',flag_present:flags.includes(r.flag||'8d84d86dd'),paired_present:flags.includes(r.paired_flag||'86dd8d84d'),hits};
}
'''
m=sub1(m,r'function parsePremiumTime\(\)\{.*?\n\}\n(?=function flush\(\))',new_premium,'premium functions')
m=m.replace("  const pt=parsePremiumTime();if(pt&&!pt.valid)warnings.push(`premiumTimePoint=${pt.raw}: 24桁(各0～3、合計32以下)の形式から外れています`);","  const pt=parsePremiumTime();if(pt&&!pt.valid)errors.push(`premiumTimePoint=${pt.raw}: 24桁(各0～3、合計32以下)の形式から外れています`);")
m=m.replace("  if(state.entries.has('addition_Number')){const v=Number(get('addition_Number'));if(!Number.isInteger(v)||v<0)warnings.push(`addition_Number=${v}: 負値/非整数`);}\n  return{ok:errors.length===0,errors,warnings};",
"  if(state.entries.has('addition_Number')){const v=Number(get('addition_Number'));if(!Number.isInteger(v)||v<0)warnings.push(`addition_Number=${v}: 負値/非整数`);}\n  const abnormal=abnormalFlagReport();for(const h of abnormal.hits)errors.push(`異常フラグ既知条件: ${h.field}=${h.current} ${h.op} ${h.value}`);if(abnormal.flag_present&&!abnormal.paired_present)warnings.push(`異常フラグ ${abnormal.flag} が保存済みです`);\n  return{ok:errors.length===0,errors,warnings,abnormal};")
m=m.replace('validateCurrent,catalogCategoryForCode,addonAllocation,setAddon,parsePremiumTime};','validateCurrent,catalogCategoryForCode,addonAllocation,setAddon,parsePremiumTime,setPremiumTime,refreshTwitterBonus,abnormalFlagReport};')
p.write_text(m)

# ---- app.js ----
p=ROOT/'js/app.js'
a=p.read_text()
a=a.replace("const BUILD='20260826-0400';","const BUILD='20260826-0500';")
a=a.replace("S.catalog=c;S.rules=r;c.items=Object.fromEntries(itemsCatalog.map(x=>[x.base_id,x]));wikiMeta=w||{};",
"S.catalog=c;S.rules=r;c.items=Object.fromEntries(itemsCatalog.map(x=>[x.base_id,x]));wikiMeta=w||{};for(const [name,meta] of Object.entries(wikiMeta.unresolved_meta||{})){const id=meta.id_guess;if(id&&/^\\d{4}$/.test(id)&&!c.items[id])c.items[id]={base_id:id,name,category_id:Number(meta.category_id),confidence:meta.guess||'inferred',source:'inferred'};}")
new_candidates=r'''function unresolvedMeta(name){return wikiMeta?.unresolved_meta?.[name]||{};}
function candidateFromName(name){const c=confirmedByName.get(name);if(c)return{kind:'confirmed',name,base_id:c.base_id,category_id:c.category_id,source:c.source,confidence:c.confidence,record:c};const u=unresolvedByName.get(name)||{},meta=unresolvedMeta(name);if(meta.id_guess&&/^\d{4}$/.test(String(meta.id_guess)))return{kind:'inferred',name,base_id:String(meta.id_guess),category_id:Number(meta.category_id||u.category_id)||null,source:u.source||'inference',confidence:meta.guess||'inferred',record:u,meta};return{kind:'unresolved',name,base_id:'',category_id:Number(u.category_id||meta.category_id)||null,source:u.source||'current-wiki',confidence:u.confidence||'unresolved',record:u,meta};}
function itemCandidates(cat,group){const ordered=wikiMeta?.ordered?.[String(cat)]?.[group];if(Array.isArray(ordered))return ordered.map(candidateFromName);return itemsCatalog.filter(x=>x.category_id===Number(cat)).sort((a,b)=>a.index-b.index).map(x=>({kind:'confirmed',name:x.name,base_id:x.base_id,category_id:x.category_id,source:x.source,confidence:x.confidence,record:x}));}
function confidenceJa(v){return({confirmed:'確定',high:'高',medium:'中',low:'低',inferred:'推定',unknown:'不明'})[v]||v||'不明';}
function fillBaseSelect(){const cat=Number($('addCategory').value||1),group=$('addGroup').value||groupsForCategory(cat)[0],list=itemCandidates(cat,group);$('addBase').innerHTML=list.map(x=>`<option data-name="${esc(x.name)}" data-kind="${x.kind}">${esc(x.name)}${x.kind==='confirmed'?` [${x.base_id}]`:x.kind==='inferred'?` [推定 ${x.base_id} / ${confidenceJa(x.confidence)}]`:' — ID不明'}</option>`).join('');syncAddItemPreview();}
function currentCandidate(){const opt=$('addBase').selectedOptions[0];return opt?candidateFromName(opt.dataset.name):null;}
function syncAddItemPreview(){const x=currentCandidate(),info=$('itemInfo'),btn=$('confirmAddItem');if(!x){info.textContent='候補がありません';btn.disabled=true;return}const meta=unresolvedMeta(x.name),writable=x.kind!=='unresolved',title=$('addTitle').value||'0003',ultra=$('addUltra').value||'0000';$('addCodePreview').textContent=writable?x.base_id+title+ultra:'ID不明';btn.disabled=!writable;
  if(x.kind==='confirmed')info.innerHTML=`<b>${esc(x.name)}</b><span class="item-status ok">ID確定</span><br><code>${esc(x.base_id)}</code> / ${esc(S.catalog?.categories?.[x.category_id]||x.category_id)}${meta.effect?`<br>${esc(meta.effect)}`:''}`;
  else if(x.kind==='inferred')info.innerHTML=`<b>${esc(x.name)}</b><span class="item-status pending">推定 ${esc(x.base_id)} / 確度 ${esc(confidenceJa(x.confidence))}</span>${meta.price?`<br>${esc(meta.price)}`:''}${meta.effect?`<br>${esc(meta.effect)}`:''}<br><span class="muted">この推定IDで書き込み可能</span>`;
  else info.innerHTML=`<b>${esc(x.name)}</b><span class="item-status pending">ID不明</span>${meta.price?`<br>${esc(meta.price)}`:''}${meta.effect?`<br>${esc(meta.effect)}`:''}`;
}
'''
a=sub1(a,r'function candidateFromName\(name\)\{.*?(?=function tabs\(\))',new_candidates,'candidate block')
a=sub1(a,r"function addItem\(\)\{.*?\n(?=function resourceNumberCard)","function addItem(){const x=currentCandidate();if(!x||x.kind==='unresolved')throw Error('内部ID不明のアイテムは追加できません');const cat=Number(x.category_id),code=x.base_id+($('addTitle').value||'0003')+($('addUltra').value||'0000'),q=Number($('addQuantity').value);if(!Number.isSafeInteger(q)||q<1)throw Error('個数は1以上の整数で指定してください');if(!S.entries.has(`items${cat}`))throw Error(`保存データにカテゴリ items${cat} がありません`);const ex=S.inventory.find(r=>r.category===cat&&r.code===code);if(ex)M.setInventory(ex,ex.quantity+q);else M.addInventory(cat,code,q);dirty();renderItems();renderSummary();toast(`${x.name}${x.kind==='inferred'?'（推定ID）':''} を追加しました`);}\n",'addItem')
new_resources=r'''function renderResources(){if(!S.outer){$('resourceForm').innerHTML='';return}const a=M.addonAllocation(),max=S.rules?.addons?.absolute_total_max??23,pt=M.parsePremiumTime(),ab=M.abnormalFlagReport();let html=resourceNumberCard('gp','GP')+resourceNumberCard('rp','RP')+resourceNumberCard('rpPoint','RP Point');if(S.entries.has('rabbit')){const v=Number(M.get('rabbit'));html+=`<div class="resource-card"><div class="range-field"><div class="range-head"><b>ラビットチケット</b><span id="rabbitOut" class="range-value">${v} / 999</span></div><input id="rabbitRange" type="range" min="0" max="999" step="1" value="${Math.max(0,Math.min(999,v))}"></div></div>`;}html+=`<div class="addon-summary"><b>アドオン</b><span id="addonTotal" class="compact-value">${a.total} / ${max}</span></div>`+a.fields.map(addonCard).join('');if(S.entries.has('adon_time'))html+=`<div class="resource-card readonly-field"><b>旧時間短縮</b><label>adon_time</label><input class="game-input" disabled value="${esc(M.get('adon_time'))}"></div>`;if(S.entries.has('addition_Number'))html+=`<div class="resource-card readonly-field"><b>内部値</b><label>addition_Number</label><input class="game-input" disabled value="${esc(M.get('addition_Number'))}"></div>`;
  if(pt){const mult=S.rules?.premium_time?.multipliers||[0.5,1,1.5,2],cells=pt.values.map((v,i)=>`<label class="premium-hour"><span>${String(i).padStart(2,'0')}時</span><select class="game-input premium-select" data-premium="${i}">${mult.map((m,j)=>`<option value="${j}" ${j===v?'selected':''}>${m}x</option>`).join('')}</select></label>`).join('');html+=`<div class="resource-card premium-card"><div class="range-head"><b>Premium Time</b><span id="premiumTotal" class="range-value">${esc(pt.total??'—')} / ${esc(S.rules?.premium_time?.total_max??32)}</span></div>${pt.valid?`<div class="premium-grid">${cells}</div>`:`<div class="notice error">形式を確認できません</div>`}</div>`;}
  const tlast=S.entries.has('twitter_last_time')?M.get('twitter_last_time'):'—';html+=`<div class="resource-card"><b>Tweet Bonus</b><span class="item-status ok">ON</span><label>twitter_last_time</label><div class="code-preview">${esc(tlast)}</div></div>`;
  const actual=ab.flag_present&&!ab.paired_present,hitCount=ab.hits.length;html+=`<div class="resource-card abnormal-card"><b>異常フラグ検証</b><span class="item-status ${actual||hitCount?'pending':'ok'}">${actual?'保存済み':hitCount?`発火条件 ${hitCount}`:'既知条件なし'}</span><div class="range-note">${esc(ab.flag)}${ab.hits.map(h=>` / ${h.field}=${h.current}`).join('')}</div></div>`;
  $('resourceForm').innerHTML=html;
  document.querySelectorAll('[data-resource-number]').forEach(i=>i.onchange=()=>{const v=Number(i.value);if(!Number.isSafeInteger(v)||v<0){renderResources();return}M.setScalar(i.dataset.resourceNumber,v);dirty();renderSummary();toast(`${i.dataset.resourceNumber} を変更しました`)});
  if($('rabbitRange')){$('rabbitRange').oninput=()=>{$('rabbitOut').textContent=`${$('rabbitRange').value} / 999`};$('rabbitRange').onchange=()=>{M.setScalar('rabbit',Number($('rabbitRange').value));dirty();renderResources();renderSummary();toast('ラビットチケットを変更しました')}}
  document.querySelectorAll('[data-addon]').forEach(i=>{i.oninput=()=>{const key=i.dataset.addon,v=Number(i.value),eff=S.rules?.addons?.effects?.[key]?.values?.[v]||'';$(`addon-out-${key}`).textContent=`${v} / 9　${eff}`};i.onchange=()=>{try{M.setAddon(i.dataset.addon,Number(i.value));dirty();renderResources();toast('アドオンを変更しました')}catch(err){toast('変更拒否: '+err.message,4200);renderResources()}}});
  document.querySelectorAll('[data-premium]').forEach(i=>i.onchange=()=>{try{const cur=M.parsePremiumTime().values.slice();cur[Number(i.dataset.premium)]=Number(i.value);M.setPremiumTime(cur);dirty();renderResources();toast('Premium Timeを変更しました')}catch(err){toast('変更拒否: '+err.message,4200);renderResources()}});
}
'''
a=sub1(a,r'function renderResources\(\)\{.*?(?=function renderEntries\(\))',new_resources,'renderResources')
a=a.replace("async function exportZip(){try{const check=validate();","async function exportZip(){try{const tw=M.refreshTwitterBonus();if(tw)dirty();const check=validate();")
a=a.replace("toast('検証済みZIPを書き出しました')","toast('検証済みZIPを書き出しました / Tweet Bonus更新済み')")
p.write_text(a)

# ---- index version ----
p=ROOT/'index.html'
i=p.read_text().replace('static v0.4.0 — v7.30 validated controls','static v0.5.0 — flags / magic / premium')
p.write_text(i)

# ---- CSS additions ----
p=ROOT/'css/v040.css'
c=p.read_text()
extra='''\n.premium-card{grid-column:1/-1}.premium-select{min-width:78px;padding:.35rem}.abnormal-card{grid-column:1/-1}.abnormal-card .range-note{word-break:break-all}.item-status.pending{white-space:nowrap}\n'''
if '.abnormal-card' not in c:c+=extra
p.write_text(c)

# ---- CI invariants ----
p=ROOT/'.github/workflows/web-validate.yml'
y=p.read_text()
needle="assert(rules.addons.per_field_min===0 && rules.addons.per_field_max===9);"
if needle in y and 'magic_creatures.json' not in y:
    y=y.replace(needle,needle+"\n            const magic=JSON.parse(fs.readFileSync('data/magic_creatures.json','utf8')); assert(magic.items.filter(x=>!x.inferred).length===37); assert(magic.items.find(x=>x.name==='オメガ').base_id==='8538'); const abnormal=JSON.parse(fs.readFileSync('data/abnormal_flags.json','utf8')); assert(abnormal.known_value_triggers.some(x=>x.field==='rabbit'&&x.value===999)); assert(rules.premium_time.editable===true);")
p.write_text(y)
