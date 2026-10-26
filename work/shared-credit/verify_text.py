"""Check source-aligned edits, preserved prior passages and exact chapter replacement."""
import difflib,json,re,sqlite3
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from prepare import BASE,WORK,OUT,ARCHIVE,C,OLD,PRIOR,write_json,sha
from pkst_codec import cid,cid_bytes,decode,encode,check_sets
def time_display(r):
    if r.get('time_format')=='epoch-decimal':
        d=Decimal(r['time']);s=int(d)
        return (datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(seconds=s,microseconds=int((d-s)*1000000))).isoformat()
    return r['time']
def verify():
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    assert json.loads((C/'catalog/current.json').read_bytes())==baseline['pointer']
    selected=json.loads((ARCHIVE/'selected-sources.json').read_bytes())
    man=json.loads((OUT/'passage-manifest.json').read_bytes())
    stats=json.loads((OUT/'editorial-statistics.json').read_bytes())
    replacement=json.loads((OUT/'replacement-manifest.json').read_bytes())
    chapterbytes=(OUT/'01-chapter.md').read_bytes();wholebytes=(OUT/'02-new-principles.md').read_bytes()
    oldbytes=(OLD/'02-new-principles.md').read_bytes();oldchapter=(OLD/'01-chapter.md').read_bytes()
    assert sha(oldbytes)==baseline['old_manuscript_sha256']==replacement['baseline_sha256']
    assert sha(oldchapter)==baseline['old_chapter_sha256']==replacement['previous_chapter_sha256']
    pos=replacement['replace_at_utf8_byte'];n=replacement['removed_bytes']
    assert oldbytes[pos:pos+n]==oldchapter
    assert oldbytes[:pos]+chapterbytes+oldbytes[pos+n:]==wholebytes
    assert wholebytes[:pos]+oldchapter+wholebytes[pos+len(chapterbytes):]==oldbytes
    assert sha(chapterbytes)==stats['chapter_sha256']==replacement['chapter_sha256']
    assert sha(wholebytes)==stats['combined_sha256']==replacement['combined_sha256']
    chapter=chapterbytes.decode();whole=wholebytes.decode()
    assert '\r' not in chapter and '\r' not in whole
    db=sqlite3.connect((BASE/baseline['pointer']['database']).as_uri()+'?mode=ro',uri=True)
    checked=set()
    def get(k):
        row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone()
        if row:
            with (BASE/row[0]).open('rb') as f:f.seek(row[1]);b=f.read(row[2])
        else:
            folder,ext=('raw','.bin') if cid_bytes(k)[1]==0x55 else ('objects','.cbor')
            b=(ARCHIVE/folder/(k+ext)).read_bytes()
        assert cid(b,cid_bytes(k)[1])==k;checked.add(k)
        if cid_bytes(k)[1]==0x55:return b
        obj=decode(b);assert encode(obj)==b;check_sets(obj);return obj
    for ref,r in selected.items():
        assert get(r['content'])['text']==r['text']
        assert sha(r['text'].encode())==r['text_sha256']
        occurrence=get(r['occurrence']);assert occurrence['event_time']==r['native_event_time']
        assert r['content'] in [x['$link'] for x in occurrence['content']]
        for k in r['anchors']:assert get(k)['occurrence']['$link']==r['occurrence']
    req=selected['CREDIT-REQUEST'];cap=req['capture'];prefix=get(cap['raw'])
    assert len(prefix)==cap['bytes'] and sha(prefix)==cap['sha256']
    record=json.loads(prefix[cap['start']:cap['end']])
    assert record['timestamp']==req['time'] and record['payload']['role']=='user'
    assert [x['text'] for x in record['payload']['content'] if x['type']=='input_text']==[req['text']]
    rebuilt='## '+man['title']+'\n\n';units=0;retained=0;old_units=[]
    for x in man['items']:
        a,b=x['chapter_span'];u,v=x['document_span']
        assert a==len(rebuilt) and chapter[a:b]==whole[u:v]==x['text']
        rebuilt+=x['text']+'\n\n'
        if x.get('previous_passage'):
            previous=x['previous_passage'];p=get(previous['cid'])
            assert p['text']==x['text'] and p['ordinal']==previous['ordinal']
            old_units.append(previous['ordinal'])
        if x.get('ref'):
            units+=1;r=selected[x['ref']];a,b=x['source_span'];source=r['text'][a:b]
            assert sha(source.encode())==x['source_sha256']
            cursor=a;pieces=[]
            for e in x['edits']:
                ea,eb=e['source_span'];oa,ob=e['output_span']
                assert cursor<=ea<=eb<=b and r['text'][ea:eb]==e['before']
                assert x['text'][oa:ob]==e['after']
                pieces.extend([r['text'][cursor:ea],e['after']]);cursor=eb
            pieces.append(r['text'][cursor:b]);assert ''.join(pieces)==x['text']
            ops=difflib.SequenceMatcher(None,source,x['text'],autojunk=False).get_opcodes()
            equal=sum(j-i for tag,i,j,k,l in ops if tag=='equal');assert equal==x['retained_characters'];retained+=equal
            assert sha((source+'changed').encode())!=x['source_sha256']
    assert rebuilt==chapter and units==stats['source_blocks'] and retained==stats['literal_aligned_source_characters']
    oldman=json.loads((OLD/'passage-manifest.json').read_bytes())
    missing={x['ordinal'] for x in oldman['items']}-set(old_units)
    assert all(oldman['items'][n].get('reason')=='节标题' for n in missing)
    assert len(old_units)==len(set(old_units))==stats['retained_previous_passages']
    assert chapter.count('\n### ')==11
    oldtext=oldchapter.decode()
    a=oldtext.index('### 十、');b=oldtext.index('### 十一、',a)
    u=chapter.index('### 十、');v=chapter.index('### 十一、',u)
    assert oldtext[:a]==chapter[:u] and oldtext[b:]==chapter[v:]
    assert (OUT/'05-section-ten.md').read_bytes()==chapter[u:v].encode()
    assert old_units==list(range(len(oldman['items'])))
    for unwanted in ['萧伯纳也说过','智能的复制成本几乎为零的时代已经不远了','我在原稿中','重新回到原稿']:
        assert unwanted not in chapter
    assert sha(chapter.replace('\n','\r\n').encode())!=stats['chapter_sha256']
    result={'schema':'sc/text-verification@1','status':'pass','recorded_at':datetime.now(timezone.utc).isoformat(),
            'chapter_sha256':stats['chapter_sha256'],'combined_sha256':stats['combined_sha256'],
            'source_entries':len(selected),'source_units_replayed':units,'passage_units':len(man['items']),
            'previous_passages_byte_preserved':len(old_units),'all_previous_body_units_preserved':True,
            'outside_chapter_byte_preserved':True,'new_request_reparsed':True,'checked_source_blocks':len(checked),
            'prior_sources':'selected immutable content, native time and anchor targets checked; original parsing relies on preceding receipts',
            'negative_checks':['source mutation changes digest','CRLF substitution changes digest'],
            'scope':'editorial text/provenance; not institutional validation or author acceptance of all edits'}
    write_json(ARCHIVE/'text-verification.json',result);db.close()
    return selected,stats,result

if __name__=='__main__':
    selected,stats,result=verify();print(json.dumps(result,ensure_ascii=False))
