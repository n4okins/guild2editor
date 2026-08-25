(function(g){
class KeyedArchive{
  constructor(root, originalBytes=null){
    if(!root || root.$archiver!=='NSKeyedArchiver' || !Array.isArray(root.$objects)) throw Error('NSKeyedArchiverではありません');
    this.root=root; this.objects=root.$objects; this.originalBytes=originalBytes; this.dirty=false;
  }
  static fromBytes(bytes){ const u=bytes instanceof Uint8Array?bytes:new Uint8Array(bytes); return new KeyedArchive(BPList.parse(u.buffer.slice(u.byteOffset,u.byteOffset+u.byteLength)),u); }
  uid(v){ return v instanceof BPList.UID?v.id:null; }
  raw(ref){ const i=typeof ref==='number'?ref:this.uid(ref); if(i===null||i<0||i>=this.objects.length) throw Error('UID範囲外'); return this.objects[i]; }
  rootRef(){ return this.root.$top?.root; }
  className(v){ const o=(v instanceof BPList.UID||typeof v==='number')?this.raw(v):v; if(!o||typeof o!=='object'||Array.isArray(o)) return null; const i=this.uid(o.$class); if(i===null) return null; const c=this.objects[i]; return c&&typeof c==='object'?c.$classname||null:null; }
  decode(v,memo=new Map([[0,null]])){
    const i=this.uid(v);
    if(i!==null){
      if(memo.has(i)) return memo.get(i);
      const o=this.raw(i);
      if(o===null||['string','number','boolean','bigint'].includes(typeof o)||o instanceof Uint8Array||o instanceof Date){memo.set(i,o);return o;}
      if(Array.isArray(o)){const a=[];memo.set(i,a);for(const x of o)a.push(this.decode(x,memo));return a;}
      if(o&&typeof o==='object'){
        const cn=this.className(o);
        if(['NSArray','NSMutableArray','NSSet','NSMutableSet','NSOrderedSet','NSMutableOrderedSet'].includes(cn)){
          const a=[];memo.set(i,a);for(const x of (o['NS.objects']||[]))a.push(this.decode(x,memo));return a;
        }
        if(['NSDictionary','NSMutableDictionary'].includes(cn)){
          const d={};memo.set(i,d);const ks=o['NS.keys']||[],vs=o['NS.objects']||[];for(let j=0;j<Math.min(ks.length,vs.length);j++)d[String(this.decode(ks[j],memo))]=this.decode(vs[j],memo);return d;
        }
        if(['NSData','NSMutableData'].includes(cn)){
          let d=o['NS.data']; if(d instanceof BPList.UID)d=this.decode(d,memo); memo.set(i,d); return d;
        }
        if(cn==='NSDate'&&typeof o['NS.time']==='number'){const d=new Date((o['NS.time']+978307200)*1000);memo.set(i,d);return d;}
        const d={};memo.set(i,d);for(const [k,x] of Object.entries(o))if(k!=='$class')d[k]=this.decode(x,memo);return d;
      }
      return o;
    }
    if(Array.isArray(v))return v.map(x=>this.decode(x,memo));
    if(v&&typeof v==='object'&&!(v instanceof Uint8Array)&&!(v instanceof Date)){const d={};for(const [k,x] of Object.entries(v))d[k]=this.decode(x,memo);return d;}
    return v;
  }
  decodeRoot(){return this.decode(this.rootRef());}
  ensureClass(name){for(let i=0;i<this.objects.length;i++){let o=this.objects[i];if(o&&typeof o==='object'&&o.$classname===name)return new BPList.UID(i);}const chains={NSMutableDictionary:['NSMutableDictionary','NSDictionary','NSObject'],NSDictionary:['NSDictionary','NSObject'],NSMutableArray:['NSMutableArray','NSArray','NSObject'],NSArray:['NSArray','NSObject'],NSMutableData:['NSMutableData','NSData','NSObject'],NSData:['NSData','NSObject']};return this.appendRaw({$classname:name,$classes:chains[name]||[name,'NSObject']});}
  appendRaw(v){this.objects.push(v);this.dirty=true;return new BPList.UID(this.objects.length-1);}
  makeRef(v){if(v===null)return new BPList.UID(0);if(['string','number','boolean'].includes(typeof v)||typeof v==='bigint')return this.appendRaw(v);if(v instanceof Uint8Array)return this.appendRaw({'NS.data':v,$class:this.ensureClass('NSMutableData')});if(Array.isArray(v))return this.appendRaw({'NS.objects':v.map(x=>this.makeRef(x)),$class:this.ensureClass('NSMutableArray')});if(v&&typeof v==='object'){const ks=[],vs=[];for(const [k,x] of Object.entries(v)){ks.push(this.makeRef(k));vs.push(this.makeRef(x));}return this.appendRaw({'NS.keys':ks,'NS.objects':vs,$class:this.ensureClass('NSMutableDictionary')});}throw Error('encode unsupported');}
  setRootValue(v){const r=this.rootRef(),i=this.uid(r); if(i!==null && ['string','number','boolean'].includes(typeof v) && ['string','number','boolean'].includes(typeof this.objects[i])){this.objects[i]=v;this.dirty=true;return;} this.root.$top.root=this.makeRef(v);this.dirty=true;}
  customSet(ref,key,v){const o=this.raw(ref),old=o[key],oi=this.uid(old);if(['number','boolean'].includes(typeof v)&&oi===null){o[key]=v;}else if(oi!==null&&['string','number','boolean'].includes(typeof this.objects[oi])&&['string','number','boolean'].includes(typeof v)){this.objects[oi]=v;}else{o[key]=this.makeRef(v);}this.dirty=true;}
  customGet(ref,key){const o=this.raw(ref);return this.decode(o[key]);}
  dictRaw(ref){const o=this.raw(ref);if(!['NSDictionary','NSMutableDictionary'].includes(this.className(o)))throw Error('dictionaryではありません');return o;}
  dictEntries(ref){const o=this.dictRaw(ref),out=[];for(let i=0;i<(o['NS.keys']||[]).length;i++)out.push([this.decode(o['NS.keys'][i]),this.decode(o['NS.objects'][i]),i]);return out;}
  dictSet(ref,key,v){const o=this.dictRaw(ref),ks=o['NS.keys']||[],vs=o['NS.objects']||[];for(let i=0;i<ks.length;i++){if(this.decode(ks[i])===key){const oi=this.uid(vs[i]);if(oi!==null&&['string','number','boolean'].includes(typeof this.objects[oi])&&['string','number','boolean'].includes(typeof v))this.objects[oi]=v;else vs[i]=this.makeRef(v);this.dirty=true;return;} }ks.push(this.makeRef(key));vs.push(this.makeRef(v));o['NS.keys']=ks;o['NS.objects']=vs;this.dirty=true;}
  dictDelete(ref,key){const o=this.dictRaw(ref),ks=o['NS.keys']||[],vs=o['NS.objects']||[];for(let i=0;i<ks.length;i++)if(this.decode(ks[i])===key){ks.splice(i,1);vs.splice(i,1);this.dirty=true;return true;}return false;}
  arrayRaw(ref){const o=this.raw(ref);if(!['NSArray','NSMutableArray','NSSet','NSMutableSet'].includes(this.className(o)))throw Error('arrayではありません');return o;}
  arrayRefs(ref){return [...(this.arrayRaw(ref)['NS.objects']||[])];}
  setArray(ref,vals){this.arrayRaw(ref)['NS.objects']=vals.map(v=>this.makeRef(v));this.dirty=true;}
  toBytes(){return BPList.write(this.root);}
}
function isBplist(u){return u instanceof Uint8Array&&new TextDecoder().decode(u.slice(0,8))==='bplist00';}
g.G2Keyed={KeyedArchive,isBplist};
})(window);
