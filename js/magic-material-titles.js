/* v0.5.6: ordinary + ultra-rare titles for category-17 magic materials. */
(function(g){
  'use strict';
  const M=g.G2Model;
  if(!M){ console.error('Guild2 magic-material title patch: G2Model is unavailable'); return; }
  const VERSION='20260829-0560';
  const $=id=>g.document.getElementById(id);
  const originalIssue=M.specialMaterialIssue.bind(M);
  const originalValidate=M.validateCurrent.bind(M);

  /* Category 17 is title-capable. Keep the old repair rule only for reserved category 18. */
  M.specialMaterialIssue=function(row){
    if(Number(row?.category)===17)return null;
    return originalIssue(row);
  };
  M.repairSpecialMaterialCodes=function(){
    const fixes=[];
    for(const row of [...M.state.inventory]){
      if(Number(row?.category)!==18)continue;
      const issue=originalIssue(row);
      if(!issue)continue;
      const a=row.archive,vals=a.decodeRoot(),existing=Number(vals?.[issue.fixed]||0);
      a.dictDelete(a.rootRef(),row.code);
      a.dictSet(a.rootRef(),issue.fixed,existing+row.quantity);
      M.ensureItemDiscovery(issue.fixed);
      fixes.push({...issue,quantity:row.quantity});
    }
    if(fixes.length){M.state.dirty=true;M.loadInventory();}
    return{changed:fixes.length,fixes,preserved_category17:true};
  };
  M.validateCurrent=function(){
    const result=originalValidate();
    const errors=(result.errors||[]).filter(msg=>!String(msg).includes('カテゴリ17は無称号固定です'));
    return{...result,errors,ok:errors.length===0};
  };

  function showToast(message,ms=3600){
    const t=$('toast');if(!t)return;
    t.textContent=message;t.classList.add('show');
    clearTimeout(t._magicTimer);t._magicTimer=setTimeout(()=>t.classList.remove('show'),ms);
  }
  function markDirty(){
    M.state.dirty=true;
    const d=$('dirtyStatus'),e=$('exportBtn');if(d)d.textContent='変更あり';if(e)e.disabled=false;
  }
  function selectedMagicMaterial(){
    const opt=$('addBase')?.selectedOptions?.[0],name=opt?.dataset?.name;
    if(!name)return null;
    return Object.values(M.state.catalog?.items||{}).find(x=>x?.name===name&&Number(x.category_id)===17)||null;
  }
  function ordinaryTitleCode(){return String(Number($('addTitle')?.value||'0003')).padStart(2,'0');}
  function ultraTitleCode(){return $('addUltra')?.value||'00';}
  function makeCode(base){return `${String(base)}${ultraTitleCode()}${ordinaryTitleCode()}0000`;}
  function refreshMagicMaterialControls(){
    if(Number($('addCategory')?.value)!==17)return;
    const title=$('addTitle'),ultra=$('addUltra'),preview=$('addCodePreview'),button=$('confirmAddItem'),info=$('itemInfo');
    if(title)title.disabled=false;if(ultra)ultra.disabled=false;
    const record=selectedMagicMaterial();
    if(!record)return;
    if(preview)preview.textContent=makeCode(record.base_id);
    if(button)button.disabled=false;
    if(info&&!info.querySelector('.magic-material-title-note')){
      info.insertAdjacentHTML('beforeend','<br><span class="muted magic-material-title-note">魔造素材は通常称号・超レア称号を保持できます。超レアスキルは魔造生物作成後も維持されます。</span>');
    }
  }
  function wrapChange(id){
    const el=$(id);if(!el)return;
    const previous=el.onchange;
    el.onchange=function(ev){const r=previous?previous.call(this,ev):undefined;queueMicrotask(refreshMagicMaterialControls);return r;};
  }
  ['addCategory','addGroup','addBase','addTitle','addUltra'].forEach(wrapChange);
  const openButton=$('addItemBtn');
  if(openButton){
    const previousOpen=openButton.onclick;
    openButton.onclick=function(ev){const r=previousOpen?previousOpen.call(this,ev):undefined;queueMicrotask(refreshMagicMaterialControls);return r;};
  }
  const confirmButton=$('confirmAddItem');
  if(confirmButton){
    const previousConfirm=confirmButton.onclick;
    confirmButton.onclick=function(ev){
      if(Number($('addCategory')?.value)!==17)return previousConfirm?previousConfirm.call(this,ev):undefined;
      ev.preventDefault();
      try{
        const record=selectedMagicMaterial();if(!record)throw Error('魔造素材IDを解決できません');
        const q=Number($('addQuantity')?.value);
        if(!Number.isSafeInteger(q)||q<1)throw Error('個数は1以上の整数で指定してください');
        if(!M.state.entries.has('items17'))throw Error('保存データにitems17がありません');
        const code=makeCode(record.base_id);
        M.addInventory(17,code,q);
        markDirty();
        $('itemSearch')?.dispatchEvent(new Event('input'));
        $('itemDialog')?.close();
        const uq=ultraTitleCode(),uqName=uq==='00'?'':M.state.catalog?.ultra_titles?.[uq];
        showToast(`${uqName?uqName+' ':''}${record.name} を追加しました / ${code} / 発見フラグ同期済み`,4800);
      }catch(err){showToast('魔造素材の追加を停止: '+err.message,5200);}
    };
  }
  queueMicrotask(refreshMagicMaterialControls);
  g.G2MagicMaterialTitles={VERSION,makeCode,refreshMagicMaterialControls};
})(window);
