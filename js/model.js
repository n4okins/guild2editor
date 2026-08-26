window.G2Model=(()=>{
const state={zip:null,tmp2:null,originalTmp3:'',outer:null,entries:new Map(),characters:[],inventory:[],dirty:false,sourceName:'',catalog:null,rules:null,location:null};
const {KeyedArchive,isBplist}=G2Keyed;
const ITEM_CODE=/^\d{12}$/;
const GROWTH_KEYS=['_p_str','_p_int','_p_men','_p_vit','_p_agi','_p_luk'];
function loadEntries(){
  state.entries.clear();
  const a=state.outer,o=a.raw(a.rootRef());
  if(!['NSDictionary','NSMutableDictionary'].includes(a.className(o)))throw Error('tmp2 rootが辞書ではありません');
  const ks=o['NS.keys']||[],vs=o['NS.objects']||[];
  for(let i=0;i<Math.min(ks.length,vs.length);i++){
    const key=a.decode(ks[i]),vi=a.uid(vs[i]);
    if(typeof key!=='string'||vi===null)continue;
    const vo=a.raw(vi);let data=vo&&vo['NS.data'];
    if(data instanceof BPList.UID)data=a.decode(data);
    if(isBplist(data)){
      try{state.entries.set(key,{key,dataObjectIndex:vi,archive:KeyedArchive.fromBytes(data)});}catch(e){console.warn('inner archive parse failed',key,e);}
    }
  }
  if(!state.entries.size)throw Error('内部セーブ項目を検出できません');
}
function entry(k){const e=state.entries.get(k);if(!e)throw Error(`項目 ${k} がありません`);return e;}
function get(k){return entry(k).archive.decodeRoot();}
function setScalar(k,v){entry(k).archive.setRootValue(v);state.dirty=true;}
function loadCharacters(){
  state.characters=[];if(!state.entries.has('groups'))return;
  const ga=entry('groups').archive,pages=ga.arrayRefs(ga.rootRef());
  for(let p=0;p<pages.length;p++)for(const [s,dr] of ga.arrayRefs(pages[p]).entries()){
    const di=ga.uid(dr);if(di===null)continue;const raw=ga.raw(di);let data=raw&&raw['NS.data'];
    if(data instanceof BPList.UID)data=ga.decode(data);if(!isBplist(data))continue;
    try{const ca=KeyedArchive.fromBytes(data);if(ca.className(ca.raw(ca.rootRef()))!=='Data_Character')continue;state.characters.push({page:p,slot:s,parentDataIndex:di,archive:ca,data:ca.decodeRoot()});}catch(e){console.warn('character parse failed',p,s,e);}
  }
}
function syncCharacter(c){const ga=entry('groups').archive;ga.raw(c.parentDataIndex)['NS.data']=c.archive.toBytes();ga.dirty=true;state.dirty=true;c.data=c.archive.decodeRoot();}
function setCharacterField(c,key,v){c.archive.customSet(c.archive.rootRef(),key,v);syncCharacter(c);}
function raceRule(lineage){return state.rules?.races?.[String(lineage)]||null;}
function levelCap(c){return raceRule(c?.data?._lineage)?.max_level??null;}
function setCharacterLevel(c,value){
  const v=Number(value),cap=levelCap(c);
  if(!Number.isSafeInteger(v)||v<1)throw Error('Lvは1以上の整数で指定してください');
  if(cap===null)throw Error('この種族/NPCはLv上限を確認できないため標準UIでは変更できません');
  if(v>cap)throw Error(`この種族のLv上限は ${cap} です`);
  c.archive.customSet(c.archive.rootRef(),'_lv',v);
  const raw=c.archive.raw(c.archive.rootRef());
  if(Object.prototype.hasOwnProperty.call(raw,'_next_exp'))c.archive.customSet(c.archive.rootRef(),'_next_exp',0);
  syncCharacter(c);
}
function setCharacterGrowth(c,key,value){
  if(!GROWTH_KEYS.includes(key))throw Error('能力値フィールドが不正です');
  const r=state.rules?.character?.growth||{min:0,max:10},v=Number(value);
  if(!Number.isSafeInteger(v)||v<r.min||v>r.max)throw Error(`${key} は ${r.min}～${r.max} の整数で指定してください`);
  c.archive.customSet(c.archive.rootRef(),key,v);syncCharacter(c);
}
function setCharacterLineage(c,value){
  const v=Number(value),r=raceRule(v);if(!Number.isSafeInteger(v)||!r)throw Error('種族IDが不正です');
  const lv=Number(c.data._lv);if(r.max_level!==null&&lv>r.max_level)throw Error(`Lv${lv}は${r.name}の上限Lv${r.max_level}を超えます。先にLvを下げてください`);
  c.archive.customSet(c.archive.rootRef(),'_lineage',v);syncCharacter(c);
}
function specialCodes(c){const v=c.archive.customGet(c.archive.rootRef(),'_specialItems');return Array.isArray(v)?v.map(String):[];}
function setTraits(c,p1,p2){
  const keep=specialCodes(c).filter(code=>{const b=Number(String(code).slice(0,4));return !(b>=8807&&b<=8821)&&!(b>=8901&&b<=8918)});
  if(p1)keep.push(String(p1).padStart(4,'0')+'00030000');if(p2)keep.push(String(p2).padStart(4,'0')+'00030000');
  const raw=c.archive.raw(c.archive.rootRef()),ref=raw._specialItems;if(ref instanceof BPList.UID)c.archive.setArray(ref,keep);else c.archive.customSet(c.archive.rootRef(),'_specialItems',keep);syncCharacter(c);
}
function nextCreateID(){const seed=Number(get('createCharacterID'));if(!Number.isInteger(seed)||seed<0)throw Error('createCharacterIDが不正です');return{seed,id:10000+seed};}
function cloneCharacter(c){
  if(!c)throw Error('複製元がありません');
  const ga=entry('groups').archive,{seed,id}=nextCreateID(),clone=KeyedArchive.fromBytes(c.archive.toBytes());
  clone.customSet(clone.rootRef(),'_createID',id);clone.customSet(clone.rootRef(),'_title',String(c.data._title||'冒険者')+' コピー');
  if(Object.prototype.hasOwnProperty.call(clone.raw(clone.rootRef()),'_number'))clone.customSet(clone.rootRef(),'_number',-1);
  const old=ga.raw(c.parentDataIndex),nr=ga.appendRaw({...old,'NS.data':clone.toBytes()}),pageRef=ga.arrayRefs(ga.rootRef())[c.page];
  ga.arrayRaw(pageRef)['NS.objects'].push(nr);ga.dirty=true;setScalar('createCharacterID',seed+1);state.dirty=true;loadCharacters();return state.characters.find(x=>Number(x.data._createID)===id)||state.characters.at(-1);
}
function clearActivePartyRefs(id){
  if(!state.entries.has('partys'))return;
  const pa=entry('partys').archive;
  for(const ref of pa.arrayRefs(pa.rootRef())){const d=pa.decode(ref);if(!d||typeof d!=='object')continue;for(let i=0;i<6;i++){const k=`${i}_createID`;if(Number(d[k])===Number(id))pa.customSet(ref,k,-1);}}
  pa.dirty=true;state.dirty=true;
}
function loadInventory(){
  state.inventory=[];
  for(let cat=0;cat<=18;cat++){const k=`items${cat}`;if(!state.entries.has(k))continue;const a=entry(k).archive,vals=a.decodeRoot();if(vals&&typeof vals==='object'&&!Array.isArray(vals))for(const [code,q] of Object.entries(vals))state.inventory.push({category:cat,code:String(code),quantity:Number(q),archive:a,key:k});}
}
function validQuantity(q){return Number.isSafeInteger(q)&&q>=0;}
function setInventory(row,q){q=Number(q);if(!validQuantity(q))throw Error('アイテム個数は0以上の整数で指定してください');const a=row.archive;if(q===0)a.dictDelete(a.rootRef(),row.code);else a.dictSet(a.rootRef(),row.code,q);state.dirty=true;loadInventory();}
function addInventory(category,code,q=1){
  category=Number(category);code=String(code);q=Number(q);
  if(!Number.isInteger(category)||category<0||category>18||!state.entries.has(`items${category}`))throw Error('アイテムカテゴリが不正です');
  if(!ITEM_CODE.test(code))throw Error('アイテムIDは12桁である必要があります');if(!validQuantity(q)||q<1)throw Error('個数は1以上の整数で指定してください');
  const k=`items${category}`,ex=state.inventory.find(r=>r.category===category&&r.code===code);if(ex)setInventory(ex,ex.quantity+q);else{entry(k).archive.dictSet(entry(k).archive.rootRef(),code,q);state.dirty=true;loadInventory();}
}
function catalogCategoryForCode(code){const base=itemParts(code).base,def=state.catalog?.items?.[base];return def?Number(def.category_id):null;}
function returnKnownEquipment(c){
  const returned=[],skipped=[];
  for(const code0 of (Array.isArray(c.data._items)?c.data._items:[])){
    const code=String(code0),cat=catalogCategoryForCode(code);
    if(cat===null||!state.entries.has(`items${cat}`)){skipped.push(code);continue;}
    addInventory(cat,code,1);returned.push(code);
  }
  return{returned,skipped};
}
function deleteCharacter(c,{returnEquipment=true}={}){
  if(!c)throw Error('削除対象がありません');const info=returnEquipment?returnKnownEquipment(c):{returned:[],skipped:[]};clearActivePartyRefs(c.data._createID);
  const ga=entry('groups').archive,pageRef=ga.arrayRefs(ga.rootRef())[c.page],arr=ga.arrayRaw(pageRef)['NS.objects'];
  if(c.slot<0||c.slot>=arr.length)throw Error('キャラクタースロットが不正です');arr.splice(c.slot,1);ga.dirty=true;state.dirty=true;loadCharacters();loadInventory();return info;
}
function flagsList(){if(!state.entries.has('flags'))return[];const v=get('flags');return Array.isArray(v)?v.map(String):[];}
function setFlagsList(values){const a=entry('flags').archive,ref=a.rootRef();a.setArray(ref,values.map(String));state.dirty=true;}
function addonPointBudget(){
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
function parsePremiumTime(){
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
  const flags=flagsList(),allocation=addonAllocation(),budget=addonPointBudget();if(allocation.total>budget.max)hits.push({field:'addon_points',op:'>',value:budget.max,current:allocation.total,flag:'sysAPov',confidence:'confirmed-v5.10-static'});
  const specific=flags.filter(x=>/^sys/.test(x));return{flag:r.flag||'8d84d86dd',paired_flag:r.paired_flag||'86dd8d84d',flag_present:flags.includes(r.flag||'8d84d86dd'),paired_present:flags.includes(r.paired_flag||'86dd8d84d'),flags,specific_flags:specific,hits,addon:allocation,addon_budget:budget};
}
function flush(){for(const e of state.entries.values())if(e.archive.dirty){state.outer.raw(e.dataObjectIndex)['NS.data']=e.archive.toBytes();state.outer.dirty=true;}return state.outer.toBytes();}
function itemParts(code){const s=String(code).padStart(12,'0');return{base:s.slice(0,4),ultra:s.slice(4,6),title:s.slice(6,8),gem:s.slice(8,12)};}
function normalTitleName(code){const c=state.catalog?.normal_titles||{},k=String(Number(code)).padStart(4,'0');return c[k]||c[code]||'';}
function ultraTitleMeta(code){return state.catalog?.ultra_title_meta?.[String(code)]||null;}
function ultraCodeFromLegacyOrdinal(n){n=Number(n);if(n>=1&&n<=70)return String(n+20).padStart(2,'0');if(n>=71&&n<=80)return String(n-61).padStart(2,'0');return null;}
function legacyUltraIssue(code){const p=itemParts(code),g=Number(p.gem);if(p.ultra!=='00'||!Number.isInteger(g)||g<1||g>80)return null;const ultra=ultraCodeFromLegacyOrdinal(g);if(!ultra)return null;return{ordinal:g,ultra,confidence:g<=70?'confirmed-v5.10-static':'inferred-high',fixed:`${p.base}${ultra}${p.title}0000`};}
function repairLegacyUltra(row){const issue=legacyUltraIssue(row.code);if(!issue)throw Error('v0.5旧形式の超レア誤書込みではありません');const q=row.quantity,a=row.archive;a.dictDelete(a.rootRef(),row.code);const existing=state.inventory.find(r=>r.category===row.category&&r.code===issue.fixed);if(existing)a.dictSet(a.rootRef(),issue.fixed,existing.quantity+q);else a.dictSet(a.rootRef(),issue.fixed,q);state.dirty=true;loadInventory();return issue;}
function itemName(code){const p=itemParts(code),c=state.catalog||{},base=c.items?.[p.base]?.name||`ID ${p.base}`,t=normalTitleName(p.title),u=c.ultra_titles?.[p.ultra]||'',g=p.gem!=='0000'?`宝石${p.gem}`:'';return [u,t==='称号なし'||t==='無称号'?'':t,base,g].filter(Boolean).join(' ');}
function summary(){return{entries:state.entries.size,characters:state.characters.length,inventory:state.inventory.length,gp:state.entries.has('gp')?get('gp'):null,rabbit:state.entries.has('rabbit')?get('rabbit'):null};}
function validateCurrent(){
  const errors=[],warnings=[],ids=new Set(),growth=state.rules?.character?.growth||{min:0,max:10};
  if(!state.outer)errors.push('セーブ未読込');
  for(const c of state.characters){
    const d=c.data,id=Number(d._createID),num=d._number,title=d._title||id;
    if(!Number.isSafeInteger(id)||id<0)errors.push(`${title}: createIDが不正`);else if(ids.has(id))errors.push(`createID重複: ${id}`);else ids.add(id);
    if(typeof num==='bigint'||!Number.isSafeInteger(Number(num)))errors.push(`${title}: _numberが安全な整数ではありません`);else if(Number(num)<-1)errors.push(`${title}: _number=${num} は不正`);
    const lv=Number(d._lv),rr=raceRule(d._lineage);if(!Number.isSafeInteger(lv)||lv<1)errors.push(`${title}: Lvが不正`);else if(rr?.max_level!==null&&rr?.max_level!==undefined&&lv>rr.max_level)errors.push(`${title}: Lv${lv} > ${rr.name}上限Lv${rr.max_level}`);else if(!rr)warnings.push(`${title}: 種族${d._lineage}のLv上限ルール未登録`);
    for(const k of GROWTH_KEYS){const v=Number(d[k]);if(!Number.isSafeInteger(v)||v<growth.min||v>growth.max)errors.push(`${title}: ${k}=${d[k]} は通常範囲${growth.min}～${growth.max}外`);}
    if(Object.prototype.hasOwnProperty.call(d,'_next_exp')){const v=Number(d._next_exp);if(!Number.isSafeInteger(v)||v<0)errors.push(`${title}: _next_expが不正`);}
    if(Object.prototype.hasOwnProperty.call(d,'_hp')){const v=Number(d._hp);if(!Number.isSafeInteger(v)||v<0)warnings.push(`${title}: 現在HP(_hp)=${d._hp} を確認してください`);}
  }
  for(const r of state.inventory){
    if(!ITEM_CODE.test(r.code))errors.push(`${r.key}: 不正なアイテムID ${r.code}`);
    if(!validQuantity(r.quantity)||r.quantity<1)errors.push(`${r.key}/${r.code}: 個数が不正`);
    const p=itemParts(r.code),gem=Number(p.gem),legacy=legacyUltraIssue(r.code);if(legacy)errors.push(`${r.code}: v0.5旧形式の超レア誤書込みです。修復候補 ${legacy.fixed}`);else if(p.gem!=='0000'&&!(Number.isInteger(gem)&&gem>=6501&&gem<=6557))errors.push(`${r.code}: gem欄 ${p.gem} は 0000 または6501～6557である必要があります`);if(p.ultra!=='00'&&!state.catalog?.ultra_titles?.[p.ultra])warnings.push(`${r.code}: 超レア/UQ ID ${p.ultra} はカタログ未登録`);
    const expected=catalogCategoryForCode(r.code);if(expected!==null&&expected!==r.category)warnings.push(`${r.code}: セーブ上カテゴリ${r.category} / カタログ定義${expected}。既存データは保持（カタログの版差・誤同定候補）`);
  }
  if(state.entries.has('partys')){
    const pa=entry('partys').archive;
    for(const ref of pa.arrayRefs(pa.rootRef())){const d=pa.decode(ref);if(!d||typeof d!=='object')continue;for(let i=0;i<6;i++){const v=Number(d[`${i}_createID`]);if(Number.isSafeInteger(v)&&v!==-1&&!ids.has(v))errors.push(`パーティ参照先が存在しません: ${v}`);}}
  }
  const add=addonAllocation(),ar=state.rules?.addons||{};for(const key of add.fields){const v=add.values[key];if(!Number.isInteger(v)||v<(ar.per_field_min??0)||v>(ar.per_field_max??9))errors.push(`${key}=${v}: 許容範囲${ar.per_field_min??0}～${ar.per_field_max??9}外`);}if(add.total>(ar.absolute_total_max??23))errors.push(`アドオン配分合計${add.total} > 理論最大${ar.absolute_total_max??23}`);
  if(state.entries.has('adon_time')){const v=Number(get('adon_time'));if(v!==0)warnings.push(`adon_time=${v}: Ver2.00で廃止された旧時間短縮配分の互換フィールド。v7.30では0維持を推奨`);}
  if(state.entries.has('rabbit')){const v=Number(get('rabbit')),rr=state.rules?.resources?.rabbit||{min:0,max:999};if(!Number.isFinite(v)||v<rr.min||v>rr.max)errors.push(`rabbit=${v}: 許容範囲${rr.min}～${rr.max}外`);}
  for(const k of ['gp','rp','rpPoint'])if(state.entries.has(k)){const v=Number(get(k));if(!Number.isSafeInteger(v)||v<0)errors.push(`${k}=${v}: 0以上の安全な整数ではありません`);}
  const pt=parsePremiumTime();if(pt&&!pt.valid)errors.push(`premiumTimePoint=${pt.raw}: 24桁(各0～3、合計32以下)の形式から外れています`);
  if(state.entries.has('addition_Number')){const v=Number(get('addition_Number'));if(!Number.isInteger(v)||v<0)warnings.push(`addition_Number=${v}: 負値/非整数`);}
  const addonBudget=addonPointBudget(),addonNow=addonAllocation();if(addonNow.total>addonBudget.max)errors.push(`アドオン合計 ${addonNow.total}pt > このセーブの解放済み上限 ${addonBudget.max}pt（sysAPov発火条件）`);
  const abnormal=abnormalFlagReport();for(const h of abnormal.hits)errors.push(`異常フラグ既知条件: ${h.field}=${h.current} ${h.op} ${h.value}`);if(abnormal.flag_present&&!abnormal.paired_present)warnings.push(`異常フラグ ${abnormal.flag} が保存済みです`);
  return{ok:errors.length===0,errors,warnings,abnormal};
}
return{state,loadEntries,loadCharacters,loadInventory,entry,get,setScalar,setCharacterField,setCharacterLevel,setCharacterGrowth,setCharacterLineage,raceRule,levelCap,setTraits,setInventory,addInventory,flush,itemParts,itemName,summary,specialCodes,cloneCharacter,deleteCharacter,validateCurrent,catalogCategoryForCode,flagsList,addonPointBudget,unlockAddonMaximum,addonAllocation,setAddon,repairAddonAbnormalFlags,parsePremiumTime,setPremiumTime,refreshTwitterBonus,abnormalFlagReport,legacyUltraIssue,repairLegacyUltra,ultraTitleMeta};
})();
