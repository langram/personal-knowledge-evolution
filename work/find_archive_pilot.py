import sqlite3,json
from pathlib import Path
root=Path(r'C:\Users\langr\Documents\Codex\2026-10-24\ni\outputs\personal-thought-archive\contributions\codex')
con=sqlite3.connect((root/'.private/windows-index.sqlite').as_uri()+'?mode=ro',uri=True)
con.row_factory=sqlite3.Row
rows=con.execute("SELECT m.*,c.text FROM message m, json_each(m.content_cids) j JOIN content c ON c.cid=j.value WHERE m.native_role='user' AND c.text LIKE ?",('%我想让将这台windows主机上的所有AI agent%',)).fetchall()
data=[dict(r) for r in rows]
(root/'.private/pilot-candidates.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'raw':r['raw'],'start':r['start'],'end':r['end'],'thread':r['thread'],'native_id':r['native_id'],'time':r['event_time'],'chars':len(r['text']),'preview':r['text'][:900]} for r in data],ensure_ascii=False))
print('Integrity:',con.execute('PRAGMA integrity_check').fetchone()[0])
print('No-message-projection:',json.dumps([dict(r) for r in con.execute("SELECT raw,thread,counts FROM source_file WHERE status='no-message-projection'")],ensure_ascii=False))
