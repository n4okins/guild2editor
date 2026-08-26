from pathlib import Path

MODEL=Path('js/model.js')
APP=Path('js/app.js')

m=MODEL.read_text()
anchor="""function addInventory(category,code,q=1){
  category=Number(category);code=String(code);q=Number(q);"""
insert="""function canonicalPlainMaterialCode(code){const p=itemParts(code);return `${p.base}00030000`;}
function specialMaterialIssue(row){if(![17,18].includes(Number(row?.category))||!ITEM_CODE.test(String(row?.code)))return null;const fixed=canonicalPlainMaterialCode(row.code);return String(row.code)===fixed?null:{fixed,category:Number(row.category),old:String(row.code)};}
function repairSpecialMaterialCodes(){
  const fixes=[];
  for(const row of [...state.inventory]){
    const issue=specialMaterialIssue(row);if(!issue)continue;const a=row.archive,vals=a.decodeRoot(),existing=Number(vals?.[issue.fixed]||0);
    a.dictDelete(a.rootRef(),row.code);a.dictSet(a.rootRef(),issue.fixed,existing+row.quantity);ensureItemDiscovery(issue.fixed);fixes.push({...issue,quantity:row.quantity});
  }
  if(fixes.length){state.dirty=true;loadInventory();}return{changed:fixes.length,fixes};
}
function addInventory(category,code,q=1){
  category=Number(category);code=String(code);q=Number(q);"""
if anchor not in m: raise SystemExit('addInventory anchor not found')
m=m.replace(anchor,insert,1)

old="""    if(!validQuantity(r.quantity)||r.quantity<1)errors.push(`${r.key}/${r.code}: 個数が不正`);
    if(discovery&&ITEM_CODE.test(r.code)){const missing=itemDiscoveryHashes(r.code).filter(h=>!discovery.has(h));if(missing.length)warnings.push(`${r.code}: flagItemsの発見フラグが${missing.length}件不足`);}"""
new="""    if(!validQuantity(r.quantity)||r.quantity<1)errors.push(`${r.key}/${r.code}: 個数が不正`);
    const materialIssue=specialMaterialIssue(r);if(materialIssue)errors.push(`${r.code}: カテゴリ${r.category}は無称号固定です。正規ID ${materialIssue.fixed}`);
    if(discovery&&ITEM_CODE.test(r.code)){const missing=itemDiscoveryHashes(r.code).filter(h=>!discovery.has(h));if(missing.length)warnings.push(`${r.code}: flagItemsの発見フラグが${missing.length}件不足`);}"""
if old not in m: raise SystemExit('validation discovery anchor not found')
m=m.replace(old,new,1)

old="""setInventory,addInventory,itemDiscoveryFlags,itemDiscoveryHashes,ensureItemDiscovery,repairInventoryDiscoveryFlags,flush"""
new="""setInventory,addInventory,itemDiscoveryFlags,itemDiscoveryHashes,ensureItemDiscovery,repairInventoryDiscoveryFlags,canonicalPlainMaterialCode,specialMaterialIssue,repairSpecialMaterialCodes,flush"""
if old not in m: raise SystemExit('model return anchor not found')
m=m.replace(old,new,1)
MODEL.write_text(m)

app=APP.read_text()
old="""async function exportZip(){try{const discoveryFix=M.repairInventoryDiscoveryFlags();if(discoveryFix.changed)dirty();const tw=M.refreshTwitterBonus();"""
new="""async function exportZip(){try{const materialFix=M.repairSpecialMaterialCodes();if(materialFix.changed)dirty();const discoveryFix=M.repairInventoryDiscoveryFlags();if(discoveryFix.changed)dirty();const tw=M.refreshTwitterBonus();"""
if old not in app: raise SystemExit('export repair anchor not found')
app=app.replace(old,new,1)
old="""toast(`検証済みZIPを書き出しました / Tweet Bonus更新済み${discoveryFix.changed?` / 発見フラグ${discoveryFix.changed}件補完`:''}`)"""
new="""toast(`検証済みZIPを書き出しました / Tweet Bonus更新済み${materialFix.changed?` / 素材ID${materialFix.changed}件修復`:''}${discoveryFix.changed?` / 発見フラグ${discoveryFix.changed}件補完`:''}`)"""
if old not in app: raise SystemExit('toast repair anchor not found')
app=app.replace(old,new,1)
APP.write_text(app)
print('material/magic follow-up applied')
