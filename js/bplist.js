/* Binary plist parser/writer for the subset used by NSKeyedArchiver. */
(function(g){
class UID{constructor(id){this.id=Number(id)}}
const te=new TextDecoder('utf-8'), td16=new TextDecoder('utf-16be');
function ube(b,p,n){let x=0;for(let i=0;i<n;i++)x=x*256+b[p+i];return x}
function i64(b,p,n){let x=0;for(let i=0;i<n;i++)x=x*256+b[p+i];return x}
function bytes(b,p,n){return b.slice(p,p+n)}
function Parser(buf){this.b=new Uint8Array(buf);this.offSize=this.b[this.b.length-26];this.refSize=this.b[this.b.length-25];this.n=Number(read64(this.b,this.b.length-24));this.top=Number(read64(this.b,this.b.length-16));this.offsets=Number(read64(this.b,this.b.length-8));this.cache=new Map();this.offsetTable=[];for(let i=0;i<this.n;i++)this.offsetTable.push(Number(read64(this.b,this.offsets+i*this.offSize,this.offSize)))}
function read64(b,p,n=8){let x=0;for(let i=0;i<n;i++)x=x*256+b[p+i];return x}
Parser.prototype.obj=function(id){if(this.cache.has(id))return this.cache.get(id);let p=this.offsetTable[id],m=this.b[p++],hi=m>>4,lo=m&15;let len=lo;if(lo===15){let mm=this.b[p++],h=mm>>4,l=mm&15;if(h!==1)throw Error('Unsupported length object');len=read64(this.b,p,2**l);p+=2**l}let out;
if(hi===0){if(lo===0)out=null;else if(lo===8)out=false;else if(lo===9)out=true;else out=null}
else if(hi===1){let n=2**lo;let x=read64(this.b,p,n);if(n===8&&x>Number.MAX_SAFE_INTEGER)x=BigInt('0x'+Array.from(this.b.slice(p,p+n)).map(x=>x.toString(16).padStart(2,'0')).join(''));out=x}
else if(hi===2){let n=2**lo;let dv=new DataView(this.b.buffer,this.b.byteOffset+p,n);out=n===4?dv.getFloat32(0,false):dv.getFloat64(0,false)}
else if(hi===3){let dv=new DataView(this.b.buffer,this.b.byteOffset+p,8);out=new Date((dv.getFloat64(0,false)+978307200)*1000)}
else if(hi===4){out=bytes(this.b,p,len)}
else if(hi===5){out=new TextDecoder('ascii').decode(bytes(this.b,p,len))}
else if(hi===6){let u=bytes(this.b,p,len*2);out=td16.decode(u)}
else if(hi===8){out=new UID(read64(this.b,p,len+1))}
else if(hi===10||hi===12){out=[];for(let i=0;i<len;i++)out.push(this.obj(read64(this.b,p+i*this.refSize,this.refSize)))}
else if(hi===13){let keys=[],vals=[];for(let i=0;i<len;i++)keys.push(this.obj(read64(this.b,p+i*this.refSize,this.refSize)));p+=len*this.refSize;for(let i=0;i<len;i++)vals.push(this.obj(read64(this.b,p+i*this.refSize,this.refSize)));out={};for(let i=0;i<len;i++)out[keys[i]]=vals[i]}
else throw Error('Unsupported bplist marker '+hi.toString(16));this.cache.set(id,out);return out}
function parse(buf){let p=new Parser(buf);return p.obj(p.top)}
function isPlain(x){return x===null||typeof x==='string'||typeof x==='number'||typeof x==='boolean'||typeof x==='bigint'||x instanceof Uint8Array||x instanceof Date||x instanceof UID||Array.isArray(x)||x&&typeof x==='object'}
function keyOrder(o){return Object.keys(o)}
function encInt(n){if(typeof n==='bigint')return {pow:Math.ceil(Math.log2(Number(n)+1)/Math.log2(2)),big:n};return {pow:n===0?0:Math.ceil(Math.log2(Math.abs(n)+1)/Math.log2(2)),big:n}}
function wlen(marker,n){if(n<15)return Uint8Array.from([marker|n]);let sz=n<256?1:n<65536?2:n<4294967296?4:8;let pow=Math.log2(sz);let a=new Uint8Array(2+sz);a[0]=marker|15;a[1]=0x10|pow;put(a,2,n,sz);return a}
function Writer(root){this.root=root;this.objs=[];this.ids=new Map();this.refSize=1}
Writer.prototype.add=function(x){if(x&&typeof x==='object'&&(x instanceof Uint8Array||x instanceof Date||x instanceof UID||Array.isArray(x)||!(x instanceof BigInt))){if(this.ids.has(x))return this.ids.get(x)}let id=this.objs.length;this.ids.set(x,id);this.objs.push(x);if(Array.isArray(x)){x.forEach(v=>this.add(v))}else if(x instanceof UID){}else if(x instanceof Date){}else if(x instanceof Uint8Array){}else if(x&&typeof x==='object'){Object.keys(x).forEach(k=>{this.add(k);this.add(x[k])})}return id}
Writer.prototype.encode=function(x){if(x===null)return Uint8Array.from([0]);if(x===false)return Uint8Array.from([8]);if(x===true)return Uint8Array.from([9]);if(typeof x==='string'){let ascii=[...x].every(c=>c.charCodeAt(0)<128);if(ascii){let a=wlen(0x50,x.length);let b=new TextEncoder().encode(x);return cat(a,b)}let b=new Uint8Array(x.length*2),dv=new DataView(b.buffer);let i=0;for(let c of x){dv.setUint16(i,c.charCodeAt(0),false);i+=2}return cat(wlen(0x60,x.length),b)}if(typeof x==='number'||typeof x==='bigint'){let n=Number(x);if(Number.isInteger(n)){if(n<0){let a=new Uint8Array(9);a[0]=0x13;let bi=BigInt(n),u=(1n<<64n)+bi;for(let i=7;i>=0;i--){a[1+i]=Number(u&255n);u>>=8n}return a}let sz=1;while(sz<8&&n>=2**(8*sz))sz*=2;let a=new Uint8Array(1+sz);a[0]=0x10+Math.log2(sz);put(a,1,n,sz);return a}let a=new Uint8Array(9);a[0]=0x23;new DataView(a.buffer).setFloat64(1,n,false);return a}if(x instanceof UID){let sz=1;while(sz<8&&x.id>=2**(8*sz))sz*=2;let a=new Uint8Array(1+sz);a[0]=0x80|(sz-1);for(let i=0;i<sz;i++)a[1+i]=Math.floor(x.id/2**(8*(sz-1-i)))&255;return a}if(x instanceof Date){let a=new Uint8Array(9);a[0]=0x33;new DataView(a.buffer).setFloat64(1,x.getTime()/1000-978307200,false);return a}if(x instanceof Uint8Array)return cat(wlen(0x40,x.length),x);if(Array.isArray(x)){let a=wlen(0xa0,x.length),refs=new Uint8Array(x.length*this.refSize);x.forEach((v,i)=>put(refs,i*this.refSize,this.ids.get(v),this.refSize));return cat(a,refs)}if(typeof x==='object'){let ks=Object.keys(x),a=wlen(0xd0,ks.length),refs=new Uint8Array(ks.length*this.refSize*2);ks.forEach((k,i)=>{put(refs,i*this.refSize,this.ids.get(k),this.refSize);put(refs,(ks.length+i)*this.refSize,this.ids.get(x[k]),this.refSize)});return cat(a,refs)}throw Error('Unsupported value')}
Writer.prototype.finish=function(){this.add(this.root);this.refSize=Math.max(1,Math.ceil(Math.log2(Math.max(1,this.objs.length))/8));let enc=this.objs.map(x=>this.encode(x)),offsets=[],pos=8;for(let e of enc){offsets.push(pos);pos+=e.length}let offsetTableOffset=pos;let offSize=1;while(2**(8*offSize)<=pos)offSize++;let ot=new Uint8Array(offsets.length*offSize);offsets.forEach((x,i)=>put(ot,i*offSize,x,offSize));let trailer=new Uint8Array(32);trailer[6]=offSize;trailer[7]=this.refSize;put(trailer,8,this.objs.length,8);put(trailer,16,this.ids.get(this.root),8);put(trailer,24,offsetTableOffset,8);return cat(new TextEncoder().encode('bplist00'),...enc,ot,trailer)}
function put(a,p,x,n){for(let i=n-1;i>=0;i--){a[p+i]=Number(x%256);x=Math.floor(x/256)}}function cat(...xs){let n=xs.reduce((s,x)=>s+x.length,0),o=new Uint8Array(n),p=0;for(let x of xs){o.set(x,p);p+=x.length}return o}
g.BPList={parse,write:x=>new Writer(x).finish(),UID,Writer};
})(window);
