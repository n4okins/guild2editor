from pathlib import Path
import json,re

ROOT=Path('.')

def sub1(text, pattern, repl, label, flags=re.S):
    out,n=re.subn(pattern,lambda _m: repl,text,count=1,flags=flags)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 replacement, got {n}')
    return out

# ---- catalog: correct item flag layout + actual unique-title IDs ----
p=ROOT/'data/catalog.json'
c=json.loads(p.read_text())
old=c['ultra_titles']
entries=sorted(((int(k),v) for k,v in old.items()),key=lambda x:x[0])
actual={}
meta={}
for ordinal,name in entries:
    if ordinal<=70:
        code=f'{ordinal+20:02d}'
        confidence='confirmed-v5.10-static'
        source='Info_Addition initWithNumber: / Data_Item uniqeWithItemFlag:'
    else:
        code=f'{ordinal-61:02d}'  # current additions: ordinal71..80 -> reserved 10..19
        confidence='inferred-high'
        source='v5.10 reserved 10..20 + current Wiki append order'
    if code in actual:
        raise SystemExit(f'ultra code collision: {code}')
    actual[code]=name
    meta[code]={'display_order':ordinal,'confidence':confidence,'source':source}
c['ultra_titles']=actual
c['ultra_title_meta']=meta
c['item_code_format']={
    'format':'BBBBUUTTGGGG',
    'base':{'start':0,'length':4},
    'unique_title':{'start':4,'length':2,'none':'00'},
    'normal_title':{'start':6,'length':2,'none':'03'},
    'gem':{'start':8,'length':4,'none':'0000','valid_min':6501,'valid_max':6557},
    'source':'Data_Item stringItemFlag:adduq:add:gem: uses %0.4d%0.2d%0.2d%0.4d; v5.10 static analysis'
}
c['data_version']='2026-08-26-v7.30-v051-itemflag-fix'
p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')

# ---- rules: derive addon max from unlock flags rather than absolute 23 ----
p=ROOT/'data/rules.json'
r=json.loads(p.read_text())
r['data_version']='2026-08-26-ranges-v4'
r.setdefault('addons',{})['budget_from_flags']={
    'base':3,
    'pow_flag_pattern':'^Guild2\\.adonPow([0-9]+)$',
    'confirmed_pow_max_v510':10,
    'business_bonus':{'Guild2.adonBisiness1':5},
    'absolute_total_max':23,
    'note':'v5.10 adonPoint_max is base 3 + adonPow1..10 each +1 + adonBisiness1 +5. Later adonPowN are counted by the same naming pattern and capped at 23; N>10 is inferred for current versions.'
}
r['abnormal_flag']={
    'flag':'8d84d86dd','paired_flag':'86dd8d84d','flags_key':'flags',
    'triggers':[
        {'field':'rabbit','op':'>','value':999,'confidence':'confirmed'},
        {'field':'adon_exp','op':'>=','value':10,'confidence':'confirmed'},
        {'field':'adon_gp','op':'>=','value':10,'confidence':'confirmed'},
        {'field':'adon_rare','op':'>=','value':10,'confidence':'confirmed'},
        {'field':'adon_time','op':'>=','value':10,'confidence':'confirmed'}
    ],
    'save_file_flags':{
        'sysAPov':{'meaning':'adonPoint_now > adonPoint_max','confidence':'confirmed-v5.10-static'},
        'sysWrit':{'meaning':'private filesystem write environment check succeeded','confidence':'confirmed-v5.10-static'},
        'sysCynst':{'meaning':'system/Cydia-style environment check','confidence':'confirmed-v5.10-static'},
        'sysRbt':{'meaning':'rabbit-related abnormal check','confidence':'confirmed-v5.10-static'}
    }
}
p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')

# ---- model ----
p=ROOT/'js/model.js'
m=p.read_text()
old_block=r"function addonAllocation\(\)\{.*?\n\}\nfunction setAddon\(key,value,budget=null\)\{.*?\n\}\n(?=function parsePremiumTime\(\))"
new_block=r'''function flagsList(){if(!state.entries.has('flags'))return[];const v=get('flags');return Array.isArray(v)?v.map(String):[];}
function setFlagsList(values){const a=entry('flags').archive,ref=a.rootRef();a.setArray(ref,values.map(String));state.dirty=true;}
function addonPointBudget(){
  const rule=state.rules?.addons||{},cfg=rule.budget_from_flags||{},flags=flagsList(),base=cfg.base??3,absolute=cfg.absolute_total_max??rule.absolute_total_max??23;
  const pow=[],unknown=[];let max=base;
  for(const f of flags){const x=/^Guild2\.adonPow(\d+)$/.exec(f);if(!x)continue;const n=Number(x[1]);if(!pow.includes(n)){pow.push(n);max+=1;if(n>(cfg.confirmed_pow_max_v510??10))unknown.push(n);}}
  const business=[];for(const [f,bonus] of Object.entries(cfg.business_bonus||{'Guild2.adonBisiness1':5}))if(flags.includes(f)){max+=Number(bonus)||0;business.push(f);}
  max=Math.min(max,absolute);pow.sort((a,b)=>a-b);return{max,absolute,base,pow,business,confidence:unknown.length?'inferred-current':'confirmed-v5.10',inferred_pow:unknown};
}
function addonAllocation(){const fields=state.rules?.addons?.current_fields||['adon_exp','adon_gp','adon_rare','adon_name'];const values={};let total=0;for(const k of fields){const v=state.entries.has(k)?Number(get(k)):0;values[k]=v;if(Number.isInteger(v))total+=v;}return{fields,values,total};}
function setAddon(key,value){
  const rule=state.rules?.addons,fields=rule?.current_fields||['adon_exp','adon_gp','adon_rare','adon_name'];if(!fields.includes(key)||!state.entries.has(key))throw Error('現在版のアドオン項目ではありません');
  const v=Number(value),min=rule?.per_field_min??0,max=rule?.per_field_max??9;if(!Number.isInteger(v)||v<min||v>max)throw Error(`${key} は ${min}～${max} の整数です`);
  const a=addonAllocation(),budget=addonPointBudget(),next=a.total-a.values[key]+v;if(next>budget.absolute)throw Error(`アドオン配分合計は絶対上限 ${budget.absolute} です`);
  if(next>budget.max&&next>=a.total)throw Error(`このセーブの解放済みアドオン上限は ${budget.max}pt です（現在/変更後 ${next}pt）。超過すると sysAPov が記録されます`);
  setScalar(key,v);return next;
}
function repairAddonAbnormalFlags(){
  const allocation=addonAllocation(),budget=addonPointBudget();if(allocation.total>budget.max)throw Error(`先にアドオン合計を ${budget.max}pt 以下へ戻してください（現在 ${allocation.total}pt）`);
  let flags=flagsList();if(!flags.includes('sysAPov'))return{changed:false,allocation,budget};
  flags=flags.filter(x=>x!=='sysAPov');const otherSys=flags.filter(x=>/^sys/.test(x));if(!otherSys.length)flags=flags.filter(x=>x!=='8d84d86dd');setFlagsList(flags);
  if(!otherSys.length&&state.entries.has('error_time'))setScalar('error_time',0);return{changed:true,allocation,budget,otherSys};
}
'''
m=sub1(m,old_block,new_block,'addon block')

old_ab=r"function abnormalFlagReport\(\)\{.*?\n\}\n(?=function flush\(\))"
new_ab=r'''function abnormalFlagReport(){
  const r=state.rules?.abnormal_flag||{},hits=[];for(const t of (r.triggers||[])){if(!state.entries.has(t.field))continue;const v=Number(get(t.field));let hit=false;if(t.op==='>')hit=v>t.value;else if(t.op==='>=')hit=v>=t.value;else if(t.op==='<')hit=v<t.value;else if(t.op==='<=')hit=v<=t.value;if(hit)hits.push({...t,current:v});}
  const flags=flagsList(),allocation=addonAllocation(),budget=addonPointBudget();if(allocation.total>budget.max)hits.push({field:'addon_points',op:'>',value:budget.max,current:allocation.total,flag:'sysAPov',confidence:'confirmed-v5.10-static'});
  const specific=flags.filter(x=>/^sys/.test(x));return{flag:r.flag||'8d84d86dd',paired_flag:r.paired_flag||'86dd8d84d',flag_present:flags.includes(r.flag||'8d84d86dd'),paired_present:flags.includes(r.paired_flag||'86dd8d84d'),flags,specific_flags:specific,hits,addon:allocation,addon_budget:budget};
}
'''
m=sub1(m,old_ab,new_ab,'abnormal block')

old_item=r"function itemParts\(code\)\{.*?\nfunction itemName\(code\)\{.*?\n\}"
new_item=r'''function itemParts(code){const s=String(code).padStart(12,'0');return{base:s.slice(0,4),ultra:s.slice(4,6),title:s.slice(6,8),gem:s.slice(8,12)};}
function normalTitleName(code){const c=state.catalog?.normal_titles||{},k=String(Number(code)).padStart(4,'0');return c[k]||c[code]||'';}
function ultraTitleMeta(code){return state.catalog?.ultra_title_meta?.[String(code)]||null;}
function ultraCodeFromLegacyOrdinal(n){n=Number(n);if(n>=1&&n<=70)return String(n+20).padStart(2,'0');if(n>=71&&n<=80)return String(n-61).padStart(2,'0');return null;}
function legacyUltraIssue(code){const p=itemParts(code),g=Number(p.gem);if(p.ultra!=='00'||!Number.isInteger(g)||g<1||g>80)return null;const ultra=ultraCodeFromLegacyOrdinal(g);if(!ultra)return null;return{ordinal:g,ultra,confidence:g<=70?'confirmed-v5.10-static':'inferred-high',fixed:`${p.base}${ultra}${p.title}0000`};}
function repairLegacyUltra(row){const issue=legacyUltraIssue(row.code);if(!issue)throw Error('v0.5旧形式の超レア誤書込みではありません');const q=row.quantity,a=row.archive;a.dictDelete(a.rootRef(),row.code);const existing=state.inventory.find(r=>r.category===row.category&&r.code===issue.fixed);if(existing)a.dictSet(a.rootRef(),issue.fixed,existing.quantity+q);else a.dictSet(a.rootRef(),issue.fixed,q);state.dirty=true;loadInventory();return issue;}
function itemName(code){const p=itemParts(code),c=state.catalog||{},base=c.items?.[p.base]?.name||`ID ${p.base}`,t=normalTitleName(p.title),u=c.ultra_titles?.[p.ultra]||'',g=p.gem!=='0000'?`宝石${p.gem}`:'';return [u,t==='称号なし'||t==='無称号'?'':t,base,g].filter(Boolean).join(' ');}
'''
m=sub1(m,old_item,new_item,'item parser')

# Add inventory-level item flag validation immediately after quantity check.
needle="    if(!validQuantity(r.quantity)||r.quantity<1)errors.push(`${r.key}/${r.code}: 個数が不正`);\n"
insert=needle+"    const p=itemParts(r.code),gem=Number(p.gem),legacy=legacyUltraIssue(r.code);if(legacy)errors.push(`${r.code}: v0.5旧形式の超レア誤書込みです。修復候補 ${legacy.fixed}`);else if(p.gem!=='0000'&&!(Number.isInteger(gem)&&gem>=6501&&gem<=6557))errors.push(`${r.code}: gem欄 ${p.gem} は 0000 または6501～6557である必要があります`);if(p.ultra!=='00'&&!state.catalog?.ultra_titles?.[p.ultra])warnings.push(`${r.code}: 超レア/UQ ID ${p.ultra} はカタログ未登録`);\n"
if needle not in m: raise SystemExit('inventory validation needle missing')
m=m.replace(needle,insert,1)

# Add per-save addon budget error before abnormal report.
needle="  const abnormal=abnormalFlagReport();"
insert="  const addonBudget=addonPointBudget(),addonNow=addonAllocation();if(addonNow.total>addonBudget.max)errors.push(`アドオン合計 ${addonNow.total}pt > このセーブの解放済み上限 ${addonBudget.max}pt（sysAPov発火条件）`);\n  const abnormal=abnormalFlagReport();"
if needle not in m: raise SystemExit('abnormal validation needle missing')
m=m.replace(needle,insert,1)

old_return="return{state,loadEntries,loadCharacters,loadInventory,entry,get,setScalar,setCharacterField,setCharacterLevel,setCharacterGrowth,setCharacterLineage,raceRule,levelCap,setTraits,setInventory,addInventory,flush,itemParts,itemName,summary,specialCodes,cloneCharacter,deleteCharacter,validateCurrent,catalogCategoryForCode,addonAllocation,setAddon,parsePremiumTime,setPremiumTime,refreshTwitterBonus,abnormalFlagReport};"
new_return="return{state,loadEntries,loadCharacters,loadInventory,entry,get,setScalar,setCharacterField,setCharacterLevel,setCharacterGrowth,setCharacterLineage,raceRule,levelCap,setTraits,setInventory,addInventory,flush,itemParts,itemName,summary,specialCodes,cloneCharacter,deleteCharacter,validateCurrent,catalogCategoryForCode,flagsList,addonPointBudget,addonAllocation,setAddon,repairAddonAbnormalFlags,parsePremiumTime,setPremiumTime,refreshTwitterBonus,abnormalFlagReport,legacyUltraIssue,repairLegacyUltra,ultraTitleMeta};"
if old_return not in m: raise SystemExit('model export return missing')
m=m.replace(old_return,new_return,1)
p.write_text(m)

# ---- app ----
p=ROOT/'js/app.js'
a=p.read_text().replace("const BUILD='20260826-0500';","const BUILD='20260826-0510';",1)
# ultra select: actual 2-digit UQ IDs and confidence
old="  $('addUltra').innerHTML='<option value=\"0000\">なし</option>'+Object.entries(c.ultra_titles).map(([k,v])=>`<option value=\"${k}\">${esc(v)} [${k}]</option>`).join('');"
new="  $('addUltra').innerHTML='<option value=\"00\">なし</option>'+Object.entries(c.ultra_titles).sort((a,b)=>(c.ultra_title_meta?.[a[0]]?.display_order??999)-(c.ultra_title_meta?.[b[0]]?.display_order??999)).map(([k,v])=>{const meta=c.ultra_title_meta?.[k]||{},conf=meta.confidence?.startsWith('confirmed')?'確定':'推定・高';return `<option value=\"${k}\">${esc(v)} [UQ ${k} / ${conf}]</option>`}).join('');"
if old not in a: raise SystemExit('app ultra select needle missing')
a=a.replace(old,new,1)
# preview and add use correct format. Replace all local constructions.
a=a.replace("const title=$('addTitle').value||'0003',ultra=$('addUltra').value||'0000';$('addCodePreview').textContent=writable?x.base_id+title+ultra:'ID不明';","const title=String(Number($('addTitle').value||'0003')).padStart(2,'0'),ultra=$('addUltra').value||'00',code=writable?x.base_id+ultra+title+'0000':'';$('addCodePreview').textContent=writable?code:'ID不明';",1)
a=a.replace("const cat=Number(x.category_id),code=x.base_id+($('addTitle').value||'0003')+($('addUltra').value||'0000'),q=Number($('addQuantity').value);","const cat=Number(x.category_id),title=String(Number($('addTitle').value||'0003')).padStart(2,'0'),ultra=$('addUltra').value||'00',code=x.base_id+ultra+title+'0000',q=Number($('addQuantity').value);",1)

# item rows: show old-v0.5 repair button
pat=r"function renderItems\(\)\{.*?\n\}"
old_match=re.search(pat,a,re.S)
if not old_match: raise SystemExit('renderItems missing')
old_render=old_match.group(0)
new_render=old_render
new_render=new_render.replace("const expected=M.catalogCategoryForCode(r.code),mismatch=expected!==null&&expected!==r.category;return `<tr><td>${esc(M.itemName(r.code))}${mismatch?`<span class=\"category-warning\">セーブ分類 ${r.category} / 定義 ${expected}</span>`:''}</td>","const expected=M.catalogCategoryForCode(r.code),mismatch=expected!==null&&expected!==r.category,legacy=M.legacyUltraIssue(r.code);return `<tr><td>${esc(M.itemName(r.code))}${mismatch?`<span class=\"category-warning\">セーブ分類 ${r.category} / 定義 ${expected}</span>`:''}${legacy?`<span class=\"category-warning\">v0.5超レア誤形式 → ${legacy.fixed}</span>`:''}</td>")
new_render=new_render.replace("<td><button class=\"game-button danger\" data-delitem=\"${S.inventory.indexOf(r)}\">削除</button></td>","<td>${legacy?`<button class=\"game-button\" data-fixultra=\"${S.inventory.indexOf(r)}\">超レア修復</button>`:''}<button class=\"game-button danger\" data-delitem=\"${S.inventory.indexOf(r)}\">削除</button></td>")
# add handler before final }
handler="document.querySelectorAll('[data-fixultra]').forEach(b=>b.onclick=()=>{try{const r=S.inventory[+b.dataset.fixultra],x=M.repairLegacyUltra(r);dirty();renderItems();toast(`超レア形式を修復: ${x.fixed}`)}catch(e){toast('修復失敗: '+e.message,4500)}});"
new_render=new_render[:-1]+handler+'}'
a=a[:old_match.start()]+new_render+a[old_match.end():]

# resources: per-save addon budget, richer abnormal UI + repair button
old="const a=M.addonAllocation(),max=S.rules?.addons?.absolute_total_max??23,pt=M.parsePremiumTime(),ab=M.abnormalFlagReport();"
new="const a=M.addonAllocation(),budget=M.addonPointBudget(),max=budget.max,pt=M.parsePremiumTime(),ab=M.abnormalFlagReport();"
if old not in a: raise SystemExit('resource header missing')
a=a.replace(old,new,1)
a=a.replace("<div class=\"addon-summary\"><b>アドオン</b><span id=\"addonTotal\" class=\"compact-value\">${a.total} / ${max}</span></div>","<div class=\"addon-summary\"><b>アドオン</b><span id=\"addonTotal\" class=\"compact-value\">${a.total} / ${max}pt 解放済み${budget.confidence==='inferred-current'?'（一部推定）':''}</span></div>",1)
old="const actual=ab.flag_present&&!ab.paired_present,hitCount=ab.hits.length;html+=`<div class=\"resource-card abnormal-card\"><b>異常フラグ検証</b><span class=\"item-status ${actual||hitCount?'pending':'ok'}\">${actual?'保存済み':hitCount?`発火条件 ${hitCount}`:'既知条件なし'}</span><div class=\"range-note\">${esc(ab.flag)}${ab.hits.map(h=>` / ${h.field}=${h.current}`).join('')}</div></div>`;"
new="const actual=ab.flag_present&&!ab.paired_present,hitCount=ab.hits.length,sys=ab.specific_flags||[];html+=`<div class=\"resource-card abnormal-card\"><b>異常フラグ検証</b><span class=\"item-status ${actual||hitCount||sys.length?'pending':'ok'}\">${sys.length?`保存済み: ${esc(sys.join(', '))}`:hitCount?`発火条件 ${hitCount}`:actual?'汎用フラグ保存済み':'既知条件なし'}</span><div class=\"range-note\">アドオン ${a.total}/${budget.max}pt / ${esc(ab.hits.map(h=>`${h.field}=${h.current}`).join(' / ')||'現在の既知発火条件なし')}</div>${sys.includes('sysAPov')?`<button id=\"repairSysAPov\" class=\"game-button\" ${a.total>budget.max?'disabled':''}>sysAPovを安全修復</button><div class=\"range-note\">${a.total>budget.max?`先に合計を${budget.max}pt以下へ戻してください`:'上限内確認後、sysAPov・単独の汎用フラグ・error_timeを修復します'}</div>`:''}</div>`;"
if old not in a: raise SystemExit('abnormal card missing')
a=a.replace(old,new,1)
# handler after resourceForm assignment
needle="  $('resourceForm').innerHTML=html;\n"
insert=needle+"  if($('repairSysAPov'))$('repairSysAPov').onclick=()=>{try{const x=M.repairAddonAbnormalFlags();dirty();renderResources();toast(x.changed?'sysAPovを修復しました':'修復対象はありません')}catch(e){toast('修復拒否: '+e.message,4800)}};\n"
if needle not in a: raise SystemExit('resource form assignment missing')
a=a.replace(needle,insert,1)
p.write_text(a)

# ---- index label ----
p=ROOT/'index.html'
h=p.read_text().replace('static v0.5.0 — flags / magic / premium','static v0.5.1 — addon budget / item flag fix')
p.write_text(h)

# ---- CI invariants ----
p=ROOT/'.github/workflows/web-validate.yml'
y=p.read_text()
needle="          if(rules.addons?.per_field_max!==9 || rules.addons?.absolute_total_max!==23) throw new Error('addon range mismatch');\n"
extra=needle+"          if(catalog.item_code_format?.format!=='BBBBUUTTGGGG') throw new Error('item flag format mismatch');\n          if(catalog.ultra_titles?.['23']!=='世界を征する'||catalog.ultra_titles?.['51']!=='引き寄せる'||catalog.ultra_titles?.['89']!=='拳で語る'||catalog.ultra_titles?.['90']!=='主を欺く') throw new Error('confirmed ultra title mapping mismatch');\n          if(catalog.ultra_titles?.['10']!=='混沌の'||catalog.ultra_title_meta?.['10']?.confidence!=='inferred-high') throw new Error('inferred current ultra mapping mismatch');\n          if(Object.keys(catalog.ultra_titles||{}).length!==80) throw new Error('ultra title count mismatch');\n          const f=['Guild2.adonPow1','Guild2.adonPow2','Guild2.adonBisiness1']; const budget=3+f.filter(x=>/^Guild2\\.adonPow\\d+$/.test(x)).length+(f.includes('Guild2.adonBisiness1')?5:0); if(budget!==10) throw new Error('addon budget derivation mismatch');\n          if(rules.addons?.budget_from_flags?.base!==3||rules.addons?.budget_from_flags?.business_bonus?.['Guild2.adonBisiness1']!==5) throw new Error('addon budget rule mismatch');\n          const build=(base,uq,tt)=>base+uq+tt+'0000'; if(build('8531','23','09')!=='853123090000'||build('6501','51','09')!=='650151090000'||build('4013','89','09')!=='401389090000') throw new Error('legacy ultra repair vectors mismatch');\n"
if needle not in y: raise SystemExit('CI needle missing')
y=y.replace(needle,extra,1)
p.write_text(y)

print('v0.5.1 fix applied')
