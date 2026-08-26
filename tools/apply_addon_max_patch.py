from pathlib import Path
import json, re

MODEL=Path('js/model.js')
APP=Path('js/app.js')
RULES=Path('data/rules.json')
INDEX=Path('index.html')

m=MODEL.read_text()
new_budget=r'''function addonPointBudget(){
  const rule=state.rules?.addons||{},cfg=rule.budget_from_flags||{},flags=flagsList(),base=cfg.base??3,absolute=cfg.absolute_total_max??rule.absolute_total_max??23,currentPowMax=cfg.current_pow_max??15,confirmedPowMax=cfg.confirmed_pow_max_v510??10;
  const pow=[],unknown=[];let max=base;
  for(const f of flags){const x=/^Guild2\.adonPow(\d+)$/.exec(f);if(!x)continue;const n=Number(x[1]);if(n>=1&&n<=currentPowMax&&!pow.includes(n)){pow.push(n);max+=1;}else if(n>currentPowMax)unknown.push(n);}
  const business=[];for(const [f,bonus] of Object.entries(cfg.business_bonus||{'Guild2.adonBisiness1':5}))if(flags.includes(f)){max+=Number(bonus)||0;business.push(f);}
  max=Math.min(max,absolute);pow.sort((a,b)=>a-b);const currentOnly=pow.filter(n=>n>confirmedPowMax);return{max,absolute,base,pow,business,confidence:currentOnly.length?'confirmed-current-spec':'confirmed-v5.10-static',current_only_pow:currentOnly,unknown_pow:unknown};
}
function unlockAddonMaximum(){
  const cfg=state.rules?.addons?.budget_from_flags||{},maxPow=cfg.current_pow_max??15,businessFlag=Object.keys(cfg.business_bonus||{'Guild2.adonBisiness1':5})[0]||'Guild2.adonBisiness1';let flags=flagsList();
  for(let n=1;n<=maxPow;n++){const f=`Guild2.adonPow${n}`;if(!flags.includes(f))flags.push(f);}if(!flags.includes(businessFlag))flags.push(businessFlag);setFlagsList(flags);return addonPointBudget();
}
'''
m,n=re.subn(r'function addonPointBudget\(\)\{.*?(?=function addonAllocation\(\))',lambda _:new_budget,m,count=1,flags=re.S)
if n!=1: raise SystemExit(f'budget block replacement failed: {n}')
m=m.replace('flagsList,addonPointBudget,addonAllocation,setAddon,repairAddonAbnormalFlags,','flagsList,addonPointBudget,unlockAddonMaximum,addonAllocation,setAddon,repairAddonAbnormalFlags,',1)
MODEL.write_text(m)

app=APP.read_text()
old="const meta=unresolvedMeta(x.name),writable=x.kind!=='unresolved',title=$('addTitle').value||'0003',ultra=$('addUltra').value||'0000';$('addCodePreview').textContent=writable?x.base_id+title+ultra:'ID不明';"
new="const meta=unresolvedMeta(x.name),writable=x.kind!=='unresolved',title=String(Number($('addTitle').value||'0003')).padStart(2,'0'),ultra=$('addUltra').value||'00';$('addCodePreview').textContent=writable?x.base_id+ultra+title+'0000':'ID不明';"
if old not in app: raise SystemExit('preview block not found')
app=app.replace(old,new,1)
needle="const actual=ab.flag_present&&!ab.paired_present,hitCount=ab.hits.length,sys=ab.specific_flags||[];html+=`<div class=\"resource-card abnormal-card\"><b>異常フラグ検証</b>"
if needle not in app: raise SystemExit('abnormal UI anchor not found')
replacement="const actual=ab.flag_present&&!ab.paired_present,hitCount=ab.hits.length,sys=ab.specific_flags||[];if(budget.max<budget.absolute)html+=`<div class=\"resource-card\"><b>アドオン上限拡張</b><span class=\"item-status pending\">${budget.max} → ${budget.absolute}pt</span><div class=\"range-note\">現行仕様の購入枠 Guild2.adonPow1..15 と Premium Pack フラグを補完します。</div><button id=\"unlockAddonMax\" class=\"game-button\">${budget.absolute}ptへ拡張</button></div>`;html+=`<div class=\"resource-card abnormal-card\"><b>異常フラグ検証</b>"
app=app.replace(needle,replacement,1)
anchor="if($('repairSysAPov'))$('repairSysAPov').onclick=()=>{try{const x=M.repairAddonAbnormalFlags();dirty();renderResources();toast(x.changed?'sysAPovを修復しました':'修復対象はありません')}catch(e){toast('修復拒否: '+e.message,4800)}};"
if anchor not in app: raise SystemExit('repair handler anchor not found')
handler="if($('unlockAddonMax'))$('unlockAddonMax').onclick=()=>{if(!confirm(`アドオン解放フラグを補完し、上限を${budget.absolute}ptへ拡張します。続行しますか？`))return;try{const b=M.unlockAddonMaximum();let repaired=false;const ar=M.abnormalFlagReport();if(ar.specific_flags?.includes('sysAPov')&&ar.addon.total<=b.max)repaired=M.repairAddonAbnormalFlags().changed;dirty();renderResources();toast(`アドオン上限を${b.max}ptへ拡張しました${repaired?' / sysAPov修復済み':''}`,4800)}catch(e){toast('上限拡張失敗: '+e.message,4800)}};"+anchor
app=app.replace(anchor,handler,1)
oldrabbit="if(state.entries.has('rabbit')){const v=Number(get('rabbit')),rr=state.rules?.resources?.rabbit||{min:0,max:999};if(!Number.isInteger(v)||v<rr.min||v>rr.max)errors.push(`rabbit=${v}: 許容範囲${rr.min}～${rr.max}外`);}"
APP.write_text(app)

m=MODEL.read_text()
if oldrabbit not in m: raise SystemExit('rabbit validation block not found')
newrabbit="if(state.entries.has('rabbit')){const v=Number(get('rabbit')),rr=state.rules?.resources?.rabbit||{min:0,max:999};if(!Number.isFinite(v)||v<rr.min||v>rr.max)errors.push(`rabbit=${v}: 許容範囲${rr.min}～${rr.max}外`);}"
m=m.replace(oldrabbit,newrabbit,1)
MODEL.write_text(m)

rules=json.loads(RULES.read_text())
a=rules['addons']
a['absolute_total_max']=23
cfg=a['budget_from_flags']
cfg['base']=3
cfg['confirmed_pow_max_v510']=10
cfg['current_pow_max']=15
cfg['business_bonus']={'Guild2.adonBisiness1':5}
cfg['absolute_total_max']=23
cfg['note']='v5.10 static analysis confirms base 3 + adonPow1..10 each +1 + adonBisiness1 +5 (=18). Current game specification permits 15 purchased points plus Premium Pack 5, so v7.30-compatible editing uses adonPow1..15 + adonBisiness1 for max 23.'
rules['data_version']='2026-08-26-ranges-v5-addon23'
rules.setdefault('evidence',{})['current_addon']='Current Wiki: initial 3 + up to 15 purchased + Premium Pack 5 = max 23; version history documents +5 purchasable points after older builds.'
RULES.write_text(json.dumps(rules,ensure_ascii=False,indent=2)+'\n')

idx=INDEX.read_text().replace('v0.5.0','v0.5.1')
INDEX.write_text(idx)
print('addon maximum patch applied')
