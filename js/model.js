window.G2Model=(()=>{
const state={zip:null,tmp2:null,originalTmp3:'',outer:null,entries:new Map(),characters:[],inventory:[],dirty:false,sourceName:'',catalog:null,location:null};
const {KeyedArchive,isBplist}=G2Keyed;
const ITEM_CODE=/^\d{12}$/;
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
function flush(){for(const e of state.entries.values())if(e.archive.dirty){state.outer.raw(e.dataObjectIndex)['NS.data']=e.archive.toBytes();state.outer.dirty=true;}return state.outer.toBytes();}
function itemParts(code){const s=String(code).padStart(12,'0');return{base:s.slice(0,4),title:s.slice(4,8),ultra:s.slice(8,12)};}
function itemName(code){const p=itemParts(code),c=state.catalog||{},base=c.items?.[p.base]?.name||`ID ${p.base}`,t=c.normal_titles?.[p.title]||'',u=c.ultra_titles?.[p.ultra]||'';return [u,t==='称号なし'||t==='無称号'?'':t,base].filter(Boolean).join(' ');}
function summary(){return{entries:state.entries.size,characters:state.characters.length,inventory:state.inventory.length,gp:state.entries.has('gp')?get('gp'):null,rabbit:state.entries.has('rabbit')?get('rabbit'):null};}
function validateCurrent(){
  const errors=[],warnings=[],ids=new Set();
  if(!state.outer)errors.push('セーブ未読込');
  for(const c of state.characters){
    const d=c.data,id=Number(d._createID),num=d._number;
    if(!Number.isSafeInteger(id)||id<0)errors.push(`${d._title||'冒険者'}: createIDが不正`);else if(ids.has(id))errors.push(`createID重複: ${id}`);else ids.add(id);
    if(typeof num==='bigint'||!Number.isSafeInteger(Number(num)))errors.push(`${d._title||id}: _numberが安全な整数ではありません`);
    else if(Number(num)<-1)errors.push(`${d._title||id}: _number=${num} は不正`);
    if(!Number.isSafeInteger(Number(d._lv))||Number(d._lv)<0)errors.push(`${d._title||id}: Lvが不正`);
  }
  for(const r of state.inventory){
    if(!ITEM_CODE.test(r.code))errors.push(`${r.key}: 不正なアイテムID ${r.code}`);
    if(!validQuantity(r.quantity)||r.quantity<1)errors.push(`${r.key}/${r.code}: 個数が不正`);
    const expected=catalogCategoryForCode(r.code);if(expected!==null&&expected!==r.category)errors.push(`${r.code}: カテゴリ${r.category}ですが定義は${expected}`);
  }
  if(state.entries.has('partys')){
    const pa=entry('partys').archive;
    for(const ref of pa.arrayRefs(pa.rootRef())){const d=pa.decode(ref);if(!d||typeof d!=='object')continue;for(let i=0;i<6;i++){const v=Number(d[`${i}_createID`]);if(Number.isSafeInteger(v)&&v!==-1&&!ids.has(v))errors.push(`パーティ参照先が存在しません: ${v}`);}}
  }
  for(const key of ['adon_exp','adon_gp','adon_rare','adon_name'])if(state.entries.has(key)){const v=Number(get(key));if(!Number.isInteger(v)||v<0||v>9)warnings.push(`${key}=${v}: 通常範囲0～9外`);}
  if(state.entries.has('addition_Number')){const v=Number(get('addition_Number'));if(!Number.isInteger(v)||v<0)warnings.push(`addition_Number=${v}: 負値/非整数`);}
  return{ok:errors.length===0,errors,warnings};
}
return{state,loadEntries,loadCharacters,loadInventory,entry,get,setScalar,setCharacterField,setTraits,setInventory,addInventory,flush,itemParts,itemName,summary,specialCodes,cloneCharacter,deleteCharacter,validateCurrent,catalogCategoryForCode};
})();
