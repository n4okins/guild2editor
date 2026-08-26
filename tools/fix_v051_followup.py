from pathlib import Path

p=Path('js/app.js')
s=p.read_text()
old="const meta=unresolvedMeta(x.name),writable=x.kind!=='unresolved',title=$('addTitle').value||'0003',ultra=$('addUltra').value||'0000';$('addCodePreview').textContent=writable?x.base_id+title+ultra:'ID不明';"
new="const meta=unresolvedMeta(x.name),writable=x.kind!=='unresolved',title=String(Number($('addTitle').value||'0003')).padStart(2,'0'),ultra=$('addUltra').value||'00',code=writable?x.base_id+ultra+title+'0000':'';$('addCodePreview').textContent=writable?code:'ID不明';"
if old not in s: raise SystemExit('preview code construction not found')
p.write_text(s.replace(old,new,1))

p=Path('js/model.js')
s=p.read_text()
old="if(state.entries.has('rabbit')){const v=Number(get('rabbit')),rr=state.rules?.resources?.rabbit||{min:0,max:999};if(!Number.isInteger(v)||v<rr.min||v>rr.max)errors.push(`rabbit=${v}: 許容範囲${rr.min}～${rr.max}外`);}"
new="if(state.entries.has('rabbit')){const v=Number(get('rabbit')),rr=state.rules?.resources?.rabbit||{min:0,max:999};if(!Number.isFinite(v)||v<rr.min||v>rr.max)errors.push(`rabbit=${v}: 許容範囲${rr.min}～${rr.max}外`);}"
if old not in s: raise SystemExit('rabbit validation not found')
p.write_text(s.replace(old,new,1))

print('follow-up fixes applied')
