from pathlib import Path
import json

MODEL=Path("js/model.js")
APP=Path("js/app.js")
WIKI=Path("data/wiki_items.json")
CI=Path(".github/workflows/web-validate.yml")
INDEX=Path("index.html")

m=MODEL.read_text()

old = """function validQuantity(q){return Number.isSafeInteger(q)&&q>=0;}
function setInventory(row,q){q=Number(q);if(!validQuantity(q))throw Error('アイテム個数は0以上の整数で指定してください');const a=row.archive;if(q===0)a.dictDelete(a.rootRef(),row.code);else a.dictSet(a.rootRef(),row.code,q);state.dirty=true;loadInventory();}
function addInventory(category,code,q=1){
  category=Number(category);code=String(code);q=Number(q);
  if(!Number.isInteger(category)||category<0||category>18||!state.entries.has(`items${category}`))throw Error('アイテムカテゴリが不正です');
  if(!ITEM_CODE.test(code))throw Error('アイテムIDは12桁である必要があります');if(!validQuantity(q)||q<1)throw Error('個数は1以上の整数で指定してください');
  const k=`items${category}`,ex=state.inventory.find(r=>r.category===category&&r.code===code);if(ex)setInventory(ex,ex.quantity+q);else{entry(k).archive.dictSet(entry(k).archive.rootRef(),code,q);state.dirty=true;loadInventory();}
}"""
new = """function validQuantity(q){return Number.isSafeInteger(q)&&q>=0;}
function setInventory(row,q){q=Number(q);if(!validQuantity(q))throw Error('アイテム個数は0以上の整数で指定してください');const a=row.archive;if(q===0)a.dictDelete(a.rootRef(),row.code);else a.dictSet(a.rootRef(),row.code,q);state.dirty=true;loadInventory();}
function itemDiscoveryFlags(){if(!state.entries.has('flagItems'))return[];const v=get('flagItems');return Array.isArray(v)?v.map(String):[];}
function itemDiscoveryHashes(code){
  code=String(code);if(!ITEM_CODE.test(code))throw Error('アイテムIDは12桁である必要があります');
  const base=String(Number(code.slice(0,4)));return [G2MD5(base),G2MD5(code)];
}
function ensureItemDiscovery(code){
  const wanted=itemDiscoveryHashes(code);if(!state.entries.has('flagItems'))return{changed:false,added:[],wanted,missingKey:true};
  const flags=itemDiscoveryFlags(),seen=new Set(flags),added=wanted.filter(h=>!seen.has(h));
  if(added.length){const a=entry('flagItems').archive;a.setArray(a.rootRef(),flags.concat(added));state.dirty=true;}
  return{changed:added.length>0,added,wanted,missingKey:false};
}
function repairInventoryDiscoveryFlags(){
  if(!state.entries.has('flagItems'))return{changed:0,items:0,added:[],missingKey:true};
  const flags=itemDiscoveryFlags(),seen=new Set(flags),added=[];let items=0;
  for(const r of state.inventory){let touched=false;for(const h of itemDiscoveryHashes(r.code))if(!seen.has(h)){seen.add(h);flags.push(h);added.push({code:r.code,hash:h});touched=true;}if(touched)items++;}
  if(added.length){const a=entry('flagItems').archive;a.setArray(a.rootRef(),flags);state.dirty=true;}
  return{changed:added.length,items,added,missingKey:false};
}
function addInventory(category,code,q=1){
  category=Number(category);code=String(code);q=Number(q);
  if(!Number.isInteger(category)||category<0||category>18||!state.entries.has(`items${category}`))throw Error('アイテムカテゴリが不正です');
  if(!ITEM_CODE.test(code))throw Error('アイテムIDは12桁である必要があります');if(!validQuantity(q)||q<1)throw Error('個数は1以上の整数で指定してください');
  const k=`items${category}`,ex=state.inventory.find(r=>r.category===category&&r.code===code);
  if(ex)ex.archive.dictSet(ex.archive.rootRef(),code,ex.quantity+q);else entry(k).archive.dictSet(entry(k).archive.rootRef(),code,q);
  ensureItemDiscovery(code);state.dirty=true;loadInventory();
}"""
if old not in m: raise SystemExit("model inventory block not found")
m=m.replace(old,new,1)

old = """function repairLegacyUltra(row){const issue=legacyUltraIssue(row.code);if(!issue)throw Error('v0.5旧形式の超レア誤書込みではありません');const q=row.quantity,a=row.archive;a.dictDelete(a.rootRef(),row.code);const existing=state.inventory.find(r=>r.category===row.category&&r.code===issue.fixed);if(existing)a.dictSet(a.rootRef(),issue.fixed,existing.quantity+q);else a.dictSet(a.rootRef(),issue.fixed,q);state.dirty=true;loadInventory();return issue;}"""
new = """function repairLegacyUltra(row){const issue=legacyUltraIssue(row.code);if(!issue)throw Error('v0.5旧形式の超レア誤書込みではありません');const q=row.quantity,a=row.archive;a.dictDelete(a.rootRef(),row.code);const existing=state.inventory.find(r=>r.category===row.category&&r.code===issue.fixed);if(existing)a.dictSet(a.rootRef(),issue.fixed,existing.quantity+q);else a.dictSet(a.rootRef(),issue.fixed,q);ensureItemDiscovery(issue.fixed);state.dirty=true;loadInventory();return issue;}"""
if old not in m: raise SystemExit("legacy repair block not found")
m=m.replace(old,new,1)

old = """  for(const r of state.inventory){
    if(!ITEM_CODE.test(r.code))errors.push(`${r.key}: 不正なアイテムID ${r.code}`);
    if(!validQuantity(r.quantity)||r.quantity<1)errors.push(`${r.key}/${r.code}: 個数が不正`);"""
new = """  const discovery=state.entries.has('flagItems')?new Set(itemDiscoveryFlags()):null;if(!discovery)warnings.push('flagItemsが見つからないため、アイテム発見状態を検証できません');
  for(const r of state.inventory){
    if(!ITEM_CODE.test(r.code))errors.push(`${r.key}: 不正なアイテムID ${r.code}`);
    if(!validQuantity(r.quantity)||r.quantity<1)errors.push(`${r.key}/${r.code}: 個数が不正`);
    if(discovery&&ITEM_CODE.test(r.code)){const missing=itemDiscoveryHashes(r.code).filter(h=>!discovery.has(h));if(missing.length)warnings.push(`${r.code}: flagItemsの発見フラグが${missing.length}件不足`);}"""
if old not in m: raise SystemExit("validation inventory anchor not found")
m=m.replace(old,new,1)

old = """return{state,loadEntries,loadCharacters,loadInventory,entry,get,setScalar,setCharacterField,setCharacterLevel,setCharacterGrowth,setCharacterLineage,raceRule,levelCap,setTraits,setInventory,addInventory,flush,itemParts,itemName,summary,specialCodes,cloneCharacter,deleteCharacter,validateCurrent,catalogCategoryForCode,flagsList,addonPointBudget,unlockAddonMaximum,addonAllocation,setAddon,repairAddonAbnormalFlags,parsePremiumTime,setPremiumTime,refreshTwitterBonus,abnormalFlagReport,legacyUltraIssue,repairLegacyUltra,ultraTitleMeta};"""
new = """return{state,loadEntries,loadCharacters,loadInventory,entry,get,setScalar,setCharacterField,setCharacterLevel,setCharacterGrowth,setCharacterLineage,raceRule,levelCap,setTraits,setInventory,addInventory,itemDiscoveryFlags,itemDiscoveryHashes,ensureItemDiscovery,repairInventoryDiscoveryFlags,flush,itemParts,itemName,summary,specialCodes,cloneCharacter,deleteCharacter,validateCurrent,catalogCategoryForCode,flagsList,addonPointBudget,unlockAddonMaximum,addonAllocation,setAddon,repairAddonAbnormalFlags,parsePremiumTime,setPremiumTime,refreshTwitterBonus,abnormalFlagReport,legacyUltraIssue,repairLegacyUltra,ultraTitleMeta};"""
if old not in m: raise SystemExit("model export block not found")
m=m.replace(old,new,1)
MODEL.write_text(m)

app=APP.read_text()
old = """function syncAddItemPreview(){const x=currentCandidate(),info=$('itemInfo'),btn=$('confirmAddItem');if(!x){info.textContent='候補がありません';btn.disabled=true;return}const meta=unresolvedMeta(x.name),writable=x.kind!=='unresolved',title=String(Number($('addTitle').value||'0003')).padStart(2,'0'),ultra=$('addUltra').value||'00';$('addCodePreview').textContent=writable?x.base_id+ultra+title+'0000':'ID不明';btn.disabled=!writable;"""
new = """function syncAddItemPreview(){const x=currentCandidate(),info=$('itemInfo'),btn=$('confirmAddItem');if(!x){info.textContent='候補がありません';btn.disabled=true;return}const meta=unresolvedMeta(x.name),writable=x.kind!=='unresolved',fixedPlain=[17,18].includes(Number(x.category_id)),title=fixedPlain?'03':String(Number($('addTitle').value||'0003')).padStart(2,'0'),ultra=fixedPlain?'00':($('addUltra').value||'00');$('addTitle').disabled=fixedPlain;$('addUltra').disabled=fixedPlain;$('addCodePreview').textContent=writable?x.base_id+ultra+title+'0000':'ID不明';btn.disabled=!writable;"""
if old not in app: raise SystemExit("preview anchor not found")
app=app.replace(old,new,1)

old = """function addItem(){const x=currentCandidate();if(!x||x.kind==='unresolved')throw Error('内部ID不明のアイテムは追加できません');const cat=Number(x.category_id),title=String(Number($('addTitle').value||'0003')).padStart(2,'0'),ultra=$('addUltra').value||'00',code=x.base_id+ultra+title+'0000',q=Number($('addQuantity').value);if(!Number.isSafeInteger(q)||q<1)throw Error('個数は1以上の整数で指定してください');if(!S.entries.has(`items${cat}`))throw Error(`保存データにカテゴリ items${cat} がありません`);const ex=S.inventory.find(r=>r.category===cat&&r.code===code);if(ex)M.setInventory(ex,ex.quantity+q);else M.addInventory(cat,code,q);dirty();renderItems();renderSummary();toast(`${x.name}${x.kind==='inferred'?'（推定ID）':''} を追加しました`);}"""
new = """function addItem(){const x=currentCandidate();if(!x||x.kind==='unresolved')throw Error('内部ID不明のアイテムは追加できません');const cat=Number(x.category_id),fixedPlain=[17,18].includes(cat),title=fixedPlain?'03':String(Number($('addTitle').value||'0003')).padStart(2,'0'),ultra=fixedPlain?'00':($('addUltra').value||'00'),code=x.base_id+ultra+title+'0000',q=Number($('addQuantity').value);if(!Number.isSafeInteger(q)||q<1)throw Error('個数は1以上の整数で指定してください');if(!S.entries.has(`items${cat}`))throw Error(`保存データにカテゴリ items${cat} がありません`);M.addInventory(cat,code,q);dirty();renderItems();renderSummary();toast(`${x.name}${x.kind==='inferred'?'（推定ID）':''} を追加しました / 発見フラグ同期済み`);}"""
if old not in app: raise SystemExit("addItem block not found")
app=app.replace(old,new,1)

old = """async function exportZip(){try{const tw=M.refreshTwitterBonus();if(tw)dirty();const check=validate();"""
new = """async function exportZip(){try{const discoveryFix=M.repairInventoryDiscoveryFlags();if(discoveryFix.changed)dirty();const tw=M.refreshTwitterBonus();if(tw)dirty();const check=validate();"""
if old not in app: raise SystemExit("export anchor not found")
app=app.replace(old,new,1)

old = """toast('検証済みZIPを書き出しました / Tweet Bonus更新済み')"""
new = """toast(`検証済みZIPを書き出しました / Tweet Bonus更新済み${discoveryFix.changed?` / 発見フラグ${discoveryFix.changed}件補完`:''}`)"""
if old not in app: raise SystemExit("export toast not found")
app=app.replace(old,new,1)
APP.write_text(app)

w=json.loads(WIKI.read_text())
groups={"エクストラ":["ウサギのしっぽ","ジェル","ネバネバ","絵本","ミサンガ","大地のドラム","ロイヤルゼリー","腰巻き","青い破片","嵐神の眼","大蛇のしっぽ","雷神の帯","クローン細胞"],"一章":["謎の骨","棘鎌","岩鱗","免許皆伝","黒い翼","伸びる蔦","銀のペンダント","捕縛の鞍","チャンピオンベルト"],"二章":["ワイングラス","古代の石","恐竜の牙","燃えさかる布","死のかけら","牛王の角","マナメタル","銀の毛皮","象牙","赤竜の鱗","氷竜の鱗","黒竜の鱗","緑竜の鱗","雷竜の鱗","銀竜の鱗","金竜の鱗"],"三章":["メダリオン","核廃棄物","裏切りの杯"],"四章":["ヒドラのしっぽ","レバノンスギ","精霊の仮面","チタニウム","執行者の証","銀の車輪","盟友の杯","獅子の腰布","アマゾネスの腰帯"],"五章":["鉄の顎","ビッグジョー","堅い皮膚","海神のひげ","亀のしっぽ","ロイヤルサイン","竜王の涙","七つ道具","虎の巻","扇子","祈祷棒","キリンの角","メデューサの首","奇妙な椅子","思い出の日記","王者の遺骨","忠義の兜","首輪","金の鍵","あぶらあげ","般若の面","荒魂"],"六章":["菩提樹の葉","フォースピラー","聖騎士の証","突撃ラッパ","力天使の翼","ねじれた角"],"七章":["竜骨","ピラミッドストーン","香水","しゃれこうべ","将軍の勲章","核の灰","ワイヤーフレーム","鷲の翼","要塞竜の鱗","霧のしずく","吸血王の牙","凍りついたアゴ髯","魔界の爵位証","殺戮衝動","エルダーサイン","高潔なる血","悪魔のしっぽ","冥界の王","大地龍の涙"]}
w.setdefault('ordered',{})['17']=groups
meta=w.setdefault('unresolved_meta',{})
n=8001
for group,names in groups.items():
    for name in names:
        item=meta.setdefault(name,{})
        item.update({'category_id':17,'group':group,'id_guess':f'{n:04d}','guess':'high','effect':'合成素材カテゴリ17の80xx帯とWiki掲載順から高確度推定。追加時は無称号固定でflagItemsも同期します。'})
        n+=1
if n!=8098: raise SystemExit(f'material count/id mismatch: next={n}')
WIKI.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n')

idx=INDEX.read_text().replace('v0.5.1','v0.5.2')
INDEX.write_text(idx)

ci=CI.read_text()
anchor="""          if(rules.addons?.per_field_max!==9 || rules.addons?.absolute_total_max!==23) throw new Error('addon range mismatch');"""
extra="""          if(rules.addons?.per_field_max!==9 || rules.addons?.absolute_total_max!==23) throw new Error('addon range mismatch');
          const mats=wiki.ordered?.['17']||{},flatMats=Object.values(mats).flat();
          if(flatMats.length!==97) throw new Error(`expected 97 synthesis materials, got ${flatMats.length}`);
          let materialId=8001;for(const name of flatMats){const m=wiki.unresolved_meta?.[name];if(m?.category_id!==17||m?.id_guess!==String(materialId).padStart(4,'0')||m?.guess!=='high')throw new Error(`material mapping mismatch ${name} -> ${m?.id_guess} expected ${materialId}`);materialId++;}
          if(wiki.unresolved_meta?.['ウサギのしっぽ']?.id_guess!=='8001'||wiki.unresolved_meta?.['絵本']?.id_guess!=='8004'||wiki.unresolved_meta?.['大地龍の涙']?.id_guess!=='8097') throw new Error('material mapping anchors mismatch');
          const model=fs.readFileSync('js/model.js','utf8'),app=fs.readFileSync('js/app.js','utf8');
          for(const s of ['itemDiscoveryHashes','ensureItemDiscovery','repairInventoryDiscoveryFlags','G2MD5(base)','G2MD5(code)']) if(!model.includes(s)) throw new Error(`missing discovery sync ${s}`);
          if(!app.includes('M.repairInventoryDiscoveryFlags()')) throw new Error('export must repair item discovery flags');
          if(!app.includes("fixedPlain=[17,18].includes")) throw new Error('material/magic IDs must be plain-title fixed');
          if(!app.includes('M.addInventory(cat,code,q)')) throw new Error('item add must use discovery-aware path');"""
if anchor not in ci: raise SystemExit("CI anchor not found")
ci=ci.replace(anchor,extra,1)
CI.write_text(ci)

print("material/magic item patch applied")
