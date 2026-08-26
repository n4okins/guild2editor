/* Load and normalize the dedicated magic-creature material catalog before app.js requests definitions. */
(function(g){
  'use strict';
  const nativeFetch = g.fetch.bind(g);
  const VERSION = '20260826-0530';
  let magicPromise = null;

  function requestPath(input){
    try{
      const raw = typeof input === 'string' ? input : input && input.url;
      return new URL(raw, g.location && g.location.href ? g.location.href : 'https://localhost/').pathname;
    }catch(_){ return ''; }
  }

  function magicDefinitions(){
    if(!magicPromise){
      magicPromise = nativeFetch(`data/magic_creatures.json?v=${VERSION}`, {cache:'no-store'})
        .then(r => { if(!r.ok) throw new Error(`magic_creatures.json: HTTP ${r.status}`); return r.json(); });
    }
    return magicPromise;
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

  function mergeItemsTsv(text, magic){
    const lines = String(text || '').replace(/\r/g,'').split('\n');
    const header = lines.shift() || '';
    const rows = lines.filter(Boolean).map(line => line.split('\t'));
    const byId = new Map(rows.map((r,i) => [r[0], i]));
    for(const item of (magic && magic.items) || []){
      const id = String(item.base_id || '');
      if(!/^\d{4}$/.test(id) || !item.name) continue;
      const row = [
        id,
        String(item.name),
        '18',
        'MagicCreature',
        item.confidence === 'confirmed' ? 'confirmed' : (item.confidence || 'high'),
        item.inferred ? 'current-wiki+sequence-inference' : 'ipa-v5.10-static+current-wiki',
        item.inferred ? 'current' : '5.10',
        'selectable'
      ];
      if(byId.has(id)) rows[byId.get(id)] = row;
      else { byId.set(id, rows.length); rows.push(row); }
    }
    return [header, ...rows.map(r => r.join('\t')), ''].join('\n');
  }

  function patchCatalog(catalog){
    if(!catalog || typeof catalog !== 'object') return catalog;
    catalog.categories = catalog.categories || {};
    catalog.categories['18'] = '魔造素材';
    catalog.data_version = `${catalog.data_version || 'unknown'}+magic-catalog-${VERSION}`;
    return catalog;
  }

  function patchWiki(wiki, magic){
    if(!wiki || typeof wiki !== 'object') wiki = {};
    const ordered = ((magic && magic.items) || [])
      .filter(x => x && x.name)
      .slice()
      .sort((a,b) => (Number(a.display_order)||999) - (Number(b.display_order)||999))
      .map(x => String(x.name));
    wiki.categories = wiki.categories || {};
    wiki.categories['18'] = {groups:['魔造生物']};
    wiki.ordered = wiki.ordered || {};
    wiki.ordered['18'] = {'魔造生物': ordered};
    return wiki;
  }

  g.G2DefinitionPreload = {VERSION, mergeItemsTsv, patchCatalog, patchWiki, magicDefinitions};

  g.fetch = async function(input, init){
    const res = await nativeFetch(input, init);
    if(!res.ok) return res;
    const path = requestPath(input);
    try{
      if(path.endsWith('/data/items.tsv') || path === 'data/items.tsv'){
        const [text, magic] = await Promise.all([res.clone().text(), magicDefinitions()]);
        return responseLike(res, mergeItemsTsv(text, magic), 'text/tab-separated-values; charset=utf-8');
      }
      if(path.endsWith('/data/catalog.json') || path === 'data/catalog.json'){
        const catalog = patchCatalog(await res.clone().json());
        return responseLike(res, JSON.stringify(catalog), 'application/json; charset=utf-8');
      }
      if(path.endsWith('/data/wiki_items.json') || path === 'data/wiki_items.json'){
        const [wiki, magic] = await Promise.all([res.clone().json(), magicDefinitions()]);
        return responseLike(res, JSON.stringify(patchWiki(wiki, magic)), 'application/json; charset=utf-8');
      }
    }catch(err){
      console.error('Guild2 definition preload failed; using original response', err);
    }
    return res;
  };
})(window);
