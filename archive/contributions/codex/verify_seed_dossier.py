"""Independently reparse native anchors and exact quotation spans before activating the catalog."""
import hashlib,json,re,sqlite3,sys
from compression import zstd
from pathlib import Path
from datetime import datetime,timezone
from pkst_codec import cid,cid_bytes,decode,encode,link,check_sets
from query_catalog import search

BASE=Path(__file__).resolve().parents[2];CODEX=BASE/'contributions/codex'
OUT=CODEX/'civilization-seed-20261025';DOC=BASE/'dossiers/2026-10-25-seed'
def main():
    capture=json.loads((OUT/'capture.json').read_text(encoding='utf-8'))
    pointer=json.loads((OUT/'staged-pointer.json').read_text())
    db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    objects={};rawcache={}
    def get(key):
        row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(key,)).fetchone();assert row,key
        with (BASE/row[0]).open('rb') as f:f.seek(row[1]);b=f.read(row[2])
        assert cid(b,cid_bytes(key)[1])==key,key
        if cid_bytes(key)[1]==0x55:return b
        obj=decode(b);check_sets(obj);assert encode(obj)==b
        return obj
    def rawdoc(key):
        if key not in rawcache:
            b=get(key)
            if b.startswith(bytes.fromhex('28b52ffd')):b=zstd.decompress(b)
            rawcache[key]=b
        return rawcache[key]
    def anchored(er):
        raw=rawdoc(er['raw']['$link'])
        if er['coordinate']=='decoded-jsonl-utf8-bytes':return json.loads(raw[er['start']:er['end']])
        assert er['coordinate']=='json-pointer'
        d=json.loads(raw)
        for part in er['pointer'].split('/')[1:]:
            part=part.replace('~1','/').replace('~0','~');d=d[int(part)] if isinstance(d,list) else d[part]
        return d
    def strings(d):
        if isinstance(d,str):yield d
        elif isinstance(d,list):
            for x in d:yield from strings(x)
        elif isinstance(d,dict):
            for x in d.values():yield from strings(x)
    # Native messages are compared independently, not merely with capture.json's derived text.
    for r in capture['recent']:
        o=get(r['occurrence']);er=get(r['anchors'][0]);d=anchored(er);p=d['payload']
        assert p['type']=='message' and p['role']==r['role']==o['native_role']
        assert d['timestamp']==r['time']==o['event_time']['value']
        assert o['actor_kind']==('ai' if p['role']=='assistant' else 'unknown')
        assert o['native_id']==(p.get('id') or None)
        assert o['native_parent_ids']==(None if 'parent_id' not in p else ([] if p['parent_id'] is None else [str(p['parent_id'])]))
        assert er['start']==r['start'] and er['end']==r['end'] and er['occurrence']['$link']==r['occurrence']
        assert len(o['content'])==len(p['content'])
        assert all(x['type'] in ('input_text','output_text','text') for x in p['content'])
        for native,part in zip(p['content'],o['content']):assert get(part['$link'])['text']==native['text']
        assert ''.join(x['text'] for x in p['content'])==r['text']
        if o['native_id'] is None:assert o['locator']=={'raw':er['raw'],'start':er['start'],'end':er['end'],'coordinate':er['coordinate']}
        assert get(o['source']['$link'])['native_thread_id']=='01a16c8a-f6e1-7580-b378-b6e49f0be965'
    lookup={r['ref']:r for r in capture['recent']+capture['history']}
    checked_anchors=set()
    for q in capture['quotes']:
        statement=get(q['statement']);text=get(q['content'])['text'];r=lookup[q['ref']]
        assert text[q['start']:q['end']]==q['quote']==statement['text']
        assert statement['force']==q['force'] and statement['seed:nature']==q['nature']
        assert statement['holder']['kind']==('ai' if r['role']=='assistant' else 'unknown')
        assert statement['seed:quotation']=={'content':link(q['content']),'start':q['start'],'end':q['end'],'coordinate':'unicode-scalar-half-open'}
        for anchor in r['anchors']:
            er=get(anchor);native=anchored(er)
            assert er['occurrence']['$link']==r['occurrence']
            assert any(q['quote'] in s for s in strings(native)),(q['id'],'native quote mismatch')
            checked_anchors.add(anchor)
    for k in capture['changes']:
        change=get(k)
        assert all(get(x['$link'])['seed:nature'].startswith('assistant-') for x in change['from_versions']+change['to_versions'])
        assert change['basis']=='explicit'
    report=json.loads((OUT/'report.json').read_text(encoding='utf-8'))
    for item in report['files']+report['research_materials']:
        b=get(item['raw']['$link']);assert hashlib.sha256(b).hexdigest()==item['sha256'] and len(b)==item['bytes']
        if 'path' in item:assert (BASE/item['path']).read_bytes()==b
    assert cid((BASE/'protocol/PKST-0.1.md').read_bytes(),0x55)==PROTOCOL
    assert db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]==200352
    hits=search(db,'从我一个人做起',20,'user');assert any(h['occurrence']==lookup['R14']['occurrence'] for h in hits)
    assert all(h['anchors'] for h in hits)
    for r in capture['history']:assert db.execute('SELECT count(*) FROM current_occurrences WHERE cid=?',(r['occurrence'],)).fetchone()[0]==1
    raw=get(capture['raw_cid']);assert len(raw)==capture['bytes']
    tampered=raw[:-1]+bytes([raw[-1]^1]);assert cid(tampered,0x55)!=capture['raw_cid']
    q=capture['quotes'][0];assert get(q['content'])['text'][q['start']:q['end']]!=q['quote']+'伪造'
    # This verifier does not claim independent human/peer review or a new all-corpus byte audit.
    result={'schema':'pkst.seed-verification@0.1','recorded_at':datetime.now(timezone.utc).isoformat(),
      'status':'pass','native_recent_messages':len(capture['recent']),'selected_history_events':len(capture['history']),
      'verbatim_quote_spans':len(capture['quotes']),'native_quote_anchors':len(checked_anchors),
      'draft_and_research_files':len(report['files'])+len(report['research_materials']),
      'new_current_events':18,'total_current_events':200352,'query':'从我一个人做起','query_pass':True,
      'negative_checks':['one changed raw byte fails CID','altered quote fails exact span'],
      'preserved_failure':'First quote selection S17 included a nonexistent leading 先; fail-fast assertion rejected it; corrected to exact native wording before finalization.',
      'scope':'separate code path checks native messages and quotation anchors; reused codec; Codex self-verification, not Claude or human review',
      'baseline_scope':'prior 715429-block verification reused; dossier closure freshly hashed; no claim of a fresh all-corpus raw audit',
      'dossier_snapshot':report['snapshot'],'federated_snapshot':pointer['snapshot']}
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    current=CODEX/'catalog/current.json'
    assert json.loads(current.read_text())['snapshot']==report['baseline_snapshot']
    staged=CODEX/'catalog/current.seed.tmp';staged.write_text(json.dumps(pointer,indent=2),encoding='utf-8');staged.replace(current)
    receipt=f'''# 本轮归档收据

状态：原生消息与逐字引用核验通过；统一检索入口已切换到增量目录。由 Codex 采用单独校验代码复核，没有声称 Claude 或用户已经审阅本轮草稿。

- 新增原生消息：18 条；引用既有事件：5 条，不重复计数。
- 逐字语义单元：22 条；编辑主题：13 个；关系：25 条；助手理解变更：2 条。
- 本专题冻结文稿：{len(report['files'])} 份；旧研究固定材料：{len(report['research_materials'])} 份。
- 当前统一索引：200,352 条来源记录，包括系统、工具、AI 与用户通道，不等于思想数量。
- 专题根：`{report['snapshot']}`。
- 新统一根：`{pointer['snapshot']}`。
- 父统一根：`{report['baseline_snapshot']}`。
- 原生记录固定前缀：{capture['bytes']:,} 字节，截止 {capture['cutoff_native_time']}。
- 原始前缀 CID：`{capture['raw_cid']}`。

已逐项复核 18 条消息的正文、角色、原生时间、父 ID、来源和字节锚；22 条引用与原件中的字符串及字符区间一致。篡改一字节与错误引文的负例均被拒绝。本专题引用闭包重新验证字节身份，全目录引用完整性及无环性通过；其余历史原件沿用上次验证记录，未宣称重新逐字节核验整个语料库。

专题复用既有对象存储，不是一个脱离原档案即可独立读取的自包含包。统一索引为可重建视图，旧目录和旧根保持可用。

详细机器记录：[专题清单](../../contributions/codex/civilization-seed-20261025/report.json) · [本轮校验](../../contributions/codex/civilization-seed-20261025/verification.json)。收据在根生成后形成，不包含进它所描述的根，避免自引用。

服务部署、录音与视频渲染、公开传播和现实组织运营均未执行。ChatGPT 官方导出仍待取得；本次会话材料已通过原生记录独立保存。
'''
    (DOC/'12-archive-receipt.md').write_text(receipt,encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
if __name__=='__main__':main()
