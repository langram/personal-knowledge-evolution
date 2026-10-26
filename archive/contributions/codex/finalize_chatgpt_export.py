"""Verify staged query semantics and retain a promotion receipt before activation."""
import json,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from pkst_codec import decode,cid,cid_bytes
from query_catalog import search

BASE=Path(__file__).resolve().parents[2];CODEX=BASE/'contributions/codex';ROOT=CODEX/'chatgpt';CAT=CODEX/'catalog'

def main():
    staged=json.loads((ROOT/'staged-pointer.json').read_text());report=json.loads((CAT/staged['report']).read_text(encoding='utf-8'))
    verification=json.loads((ROOT/'verification-v1.json').read_text(encoding='utf-8'));assert verification['status']=='pass'
    db=sqlite3.connect((BASE/staged['database']).as_uri()+'?mode=ro',uri=True)
    expected=report['unique_current_events'];assert db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]==expected==212351
    assert db.execute("SELECT count(*) FROM current_occurrences o JOIN sources s ON s.cid=o.source WHERE s.platform='chatgpt'").fetchone()[0]==11999
    text_bearing=db.execute("SELECT count(DISTINCT o.cid) FROM current_occurrences o JOIN sources s ON s.cid=o.source JOIN parts p ON p.occurrence=o.cid JOIN content c ON c.cid=p.content WHERE s.platform='chatgpt'").fetchone()[0]
    searchable=db.execute("SELECT count(DISTINCT o.cid) FROM current_occurrences o JOIN sources s ON s.cid=o.source JOIN parts p ON p.occurrence=o.cid JOIN content c ON c.cid=p.content WHERE s.platform='chatgpt' AND length(c.text)>0").fetchone()[0]
    capture=json.loads((ROOT/'capture-current.json').read_text());members=[json.loads(x) for x in (ROOT/capture['manifest']).read_text(encoding='utf-8').splitlines()]
    expected_text=0;expected_nonempty=0;expected_imageonly=0
    for member in members:
        if not member['member_name'].startswith('conversations-'):continue
        for conversation in json.loads((ROOT/'raw'/(member['raw_cid']+'.bin')).read_bytes()):
            for node in conversation['mapping'].values():
                message=node.get('message')
                if not message or message['content']['content_type'] not in ('text','multimodal_text'):continue
                text=[x for x in message['content']['parts'] if isinstance(x,str)]
                expected_text+=bool(text);expected_nonempty+=any(len(x)>0 for x in text);expected_imageonly+=not text
    assert text_bearing==expected_text==8240 and searchable==expected_nonempty==8227 and expected_imageonly==12
    evidence=json.loads((BASE/json.loads((ROOT/'import-report-v1.json').read_text())['anchors']).read_text(encoding='utf-8'))
    opaque=[x['occurrence'] for x in evidence['anchors'] if x['type'] in ('thoughts','reasoning_recap')];assert len(opaque)==3747
    for k in opaque:assert db.execute('SELECT count(*) FROM parts p JOIN content c ON c.cid=p.content WHERE p.occurrence=?',(k,)).fetchone()[0]==0
    queries={}
    for term in ['关于自我实现的科幻作品的设想','个体需求部分','这个神经元的突触']:
        rows=search(db,term,100,'user','chatgpt');assert rows and all(x['platform']=='chatgpt' and x['native_role']=='user' and x['anchors'] for x in rows)
        queries[term]=[x['occurrence'] for x in rows]
    assert not search(db,'PKST-impossible-query-e3883dce',5,platform='chatgpt')
    allhits=search(db,'关于自我实现的科幻作品的设想',100)
    assert set(queries['关于自我实现的科幻作品的设想'])<={x['occurrence'] for x in allhits}
    overlap_threads=db.execute("SELECT count(DISTINCT a.native_thread_id) FROM sources a JOIN sources b ON a.native_thread_id=b.native_thread_id WHERE a.platform='chatgpt' AND b.platform!='chatgpt'").fetchone()[0]
    other_ids={(t,i) for t,i in db.execute("SELECT s.native_thread_id,o.native_id FROM current_occurrences o JOIN sources s ON s.cid=o.source WHERE s.platform!='chatgpt' AND o.native_id IS NOT NULL")}
    overlaps=sum((t,i) in other_ids for t,i in db.execute("SELECT s.native_thread_id,o.native_id FROM current_occurrences o JOIN sources s ON s.cid=o.source WHERE s.platform='chatgpt' AND o.native_id IS NOT NULL"))
    candidate_groups=db.execute("SELECT count(DISTINCT c.content) FROM candidates c JOIN parts p ON p.content=c.content JOIN current_occurrences o ON o.cid=p.occurrence JOIN sources s ON s.cid=o.source WHERE s.platform='chatgpt'").fetchone()[0]
    history=db.execute('SELECT count(*) FROM occurrences WHERE cid NOT IN (SELECT cid FROM current_occurrences)').fetchone()[0];assert history>0
    for name,counts in report['current_counts_by_collection'].items():
        actual=dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema',(name,)))
        assert actual==counts,name
    assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(staged['snapshot'],)).fetchone()
    with (BASE/row[0]).open('rb') as f:f.seek(row[1]);b=f.read(row[2])
    assert cid(b)==staged['snapshot'];snapshot=decode(b);assert snapshot['parents']==[{'$link':report['baseline_snapshot']}]
    result={'schema':'pkst.chatgpt-catalog-acceptance@0.1','recorded_at':datetime.now(timezone.utc).isoformat(),'status':'pass',
        'snapshot':staged['snapshot'],'baseline_snapshot':report['baseline_snapshot'],'total_current_source_events':expected,'chatgpt_records':11999,
        'chatgpt_nonempty_searchable_messages':searchable,'chatgpt_messages_with_native_text_part':text_bearing,'image_only_messages':expected_imageonly,'empty_text_messages':text_bearing-searchable,
        'opaque_records_excluded':len(opaque),'queries':queries,'historical_events_excluded':history,
        'exact_long_text_candidate_groups':report['exact_long_text_candidate_groups'],'candidate_groups_involving_chatgpt':candidate_groups,
        'same_thread_id_in_other_platforms':overlap_threads,'same_thread_and_message_id_in_other_platforms':overlaps,
        'all_collection_membership_counts_unchanged_except_new_chatgpt':True,'source_verification':'verification-v1.json',
        'preserved_failure':'Initial acceptance expected all 8252 nonopaque messages to contain text; assertion rejected activation. Native reinspection found 12 image-only messages and 13 empty-text messages; count now derives from original source.',
        'limitations':['Source records are not unique real-world utterances or thoughts','Cross-source exact text does not establish copy direction or authorship','Only new blocks freshly hashed; old bytes rely on previous verification','No peer or human review']}
    (ROOT/'catalog-acceptance-v1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    current=CAT/'current.json';prior=json.loads(current.read_text());assert prior['snapshot']==report['baseline_snapshot']
    (ROOT/'prior-catalog-pointer.json').write_bytes(current.read_bytes())
    temp=CAT/'current-chatgpt-v1.tmp';temp.write_text(json.dumps(staged,indent=2),encoding='utf-8');temp.replace(current)
    status=ROOT/'source-status.json';(ROOT/'source-status-before-import.json').write_bytes(status.read_bytes())
    status.write_text(json.dumps({'schema':'pkst.source-status@0.1','recorded_at':result['recorded_at'],'owner':'codex','platform':'chatgpt','namespace':'owner-openai-account',
        'export':{'status':'official-archive-received','evidence_kind':'downloaded-local-ZIP','email_ready_time':'user reports received about 19 hours before this turn; not independently inspected'},
        'download':{'status':'captured-verified','actual_archive_received':True,'archive_bytes':958001574,'members':369},
        'processing':{'status':'imported-verified-indexed','conversations':431,'records':11999,'native_text_or_multimodal_messages':8252,'opaque_records':3747,'parent_disagreements':3980,'unresolved_attachment_references':114,
        'root':verification['snapshot'],'catalog':staged['snapshot'],'acceptance':'catalog-acceptance-v1.json'},
        'coverage':'All members and all conversation shards in this ZIP; deleted or omitted account history unknown; full semantic extraction not performed.','privacy':'local-only','public_release':False},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
