/* Correct v7.30 warehouse material namespaces before app.js loads definitions. */
(function(g){
  'use strict';
  const nativeFetch = g.fetch.bind(g);
  const VERSION = '20260826-0540';
  let overridePromise = null;

  function requestPath(input){
    try{
      const raw = typeof input === 'string' ? input : input && input.url;
      return new URL(raw, g.location && g.location.href ? g.location.href : 'https://localhost/').pathname;
    }catch(_){ return ''; }
  }

  function materialOverrides(){
    if(!overridePromise){
      overridePromise = nativeFetch(`data/current_material_overrides.json?v=${VERSION}`, {cache:'no-store'})
        .then(r => { if(!r.ok) throw new Error(`current_material_overrides.json: HTTP ${r.status}`); return r.json(); });
    }
    return overridePromise;
  }

  function responseLike(source, body, contentType){
    const headers = new Headers(source.headers);
    if(contentType) headers.set('content-type', contentType);
    headers.set('x-guild2-definition-patch', VERSION);
    return new Response(body, {
      status: source.status,
      statusText: source.statusText,
      headers
    });
  }

  function isLegacyCreatureCatalogRow(row){
    const id = Number(row && row[0]);
    return row && row[3] === 'MagicCreature' && id >= 8501 && id <= 8538;
  }

  function mergeItemsTsv(text, overrides){
    const lines = String(text || '').replace(/\r/g,'').split('\n');
    const header = lines.shift() || '';
    const rows = lines.filter(Boolean).map(line => line.split('\t')).filter(row => !isLegacyCreatureCatalogRow(row));
    const byId = new Map(rows.map((r,i) => [r[0], i]));

    for(const item of (overrides && overrides.items) || []){
      if(item.confidence !== 'confirmed') continue;
      const id = String(item.base_id || '');
      if(!/^\d{4}$/.test(id) || !item.name) continue;
      const row = [
        id,
        String(item.name),
        String(item.category_id),
        String(item.subgroup || 'Material'),
        'confirmed',
        String(item.source || 'current-save+screenshots'),
        String(overrides.observed_version || 'current'),
        'selectable'
      ];
      if(byId.has(id)) rows[byId.get(id)] = row;
      else { byId.set(id, rows.length); rows.push(row); }
    }
    return [header, ...rows.map(r => r.join('\t')), ''].join('\n');
  }

  function patchCatalog(catalog, overrides){
    if(!catalog || typeof catalog !== 'object') return catalog;
    catalog.categories = catalog.categories || {};
    for(const [id,name] of Object.entries((overrides && overrides.categories) || {})) catalog.categories[id] = name;
    catalog.data_version = `${catalog.data_version || 'unknown'}+v730-material-${VERSION}`;
    return catalog;
  }

  function clearRejectedSequentialGuesses(meta){
    if(!meta || typeof meta !== 'object') return;
    for(const m of Object.values(meta)){
      const id = Number(m && m.id_guess);
      if(Number(m && m.category_id) === 17 && id >= 8001 && id <= 8097){
        delete m.id_guess;
        m.guess = 'rejected-v730-save';
      }
    }
  }

  function patchWiki(wiki, overrides){
    if(!wiki || typeof wiki !== 'object') wiki = {};
    wiki.categories = wiki.categories || {};
    wiki.ordered = wiki.ordered || {};
    wiki.unresolved_meta = wiki.unresolved_meta || {};

    clearRejectedSequentialGuesses(wiki.unresolved_meta);

    wiki.categories['16'] = {groups:['合成アイテム（エクストラ）','合成アイテム（一章）']};
    wiki.categories['17'] = {groups:['魔造生物']};
    wiki.categories['18'] = {groups:[]};

    wiki.ordered['16'] = {
      '合成アイテム（エクストラ）': ['ウサギのしっぽ'],
      '合成アイテム（一章)': ['棘鎌','岩鱗']
    };
    wiki.ordered['17'] = {'魔造生物':['ゴリアテ','ホワイトドラゴン']};
    wiki.ordered['18'] = {};

    for(const item of (overrides && overrides.items) || []){
      if(item.confidence === 'confirmed') continue;
      wiki.unresolved_meta[item.name] = {
        ...(wiki.unresolved_meta[item.name] || {}),
        category_id: Number(item.category_id),
        id_guess: String(item.base_id),
        guess: item.confidence || 'high',
        source: item.source || 'current-save+screenshots',
        effect: wiki.unresolved_meta[item.name]?.effect || ''
      };
    }
    return wiki;
  }

  g.G2DefinitionPreload = {VERSION, mergeItemsTsv, patchCatalog, patchWiki, materialOverrides};

  g.fetch = async function(input, init){
    const res = await nativeFetch(input, init);
    if(!res.ok) return res;
    const path = requestPath(input);
    try{
      if(path.endsWith('/data/items.tsv') || path === 'data/items.tsv'){
        const [text, overrides] = await Promise.all([res.clone().text(), materialOverrides()]);
        return responseLike(res, mergeItemsTsv(text, overrides), 'text/tab-separated-values; charset=utf-8');
      }
      if(path.endsWith('/data/catalog.json') || path === 'data/catalog.json'){
        const [catalog, overrides] = await Promise.all([res.clone().json(), materialOverrides()]);
        return responseLike(res, JSON.stringify(patchCatalog(catalog, overrides)), 'application/json; charset=utf-8');
      }
      if(path.endsWith('/data/wiki_items.json') || path === 'data/wiki_items.json'){
        const [wiki, overrides] = await Promise.all([res.clone().json(), materialOverrides()]);
        return responseLike(res, JSON.stringify(patchWiki(wiki, overrides)), 'application/json; charset=utf-8');
      }
    }catch(err){
      console.error('Guild2 v7.30 material definition patch failed; using original response', err);
    }
    return res;
  };
})(window);
