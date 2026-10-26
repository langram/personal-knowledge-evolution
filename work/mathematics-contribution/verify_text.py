"""Replay native request, selected source intervals, edits and book insertion."""
import difflib, json, re, sqlite3
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from prepare import BASE, WORK, OUT, ARCHIVE, C, write_json, sha
from pkst_codec import cid, cid_bytes, decode, encode, check_sets

def source_time(r):
    if r.get('time_format')=='epoch-decimal':
        d=Decimal(r['time']);s=int(d);us=int((d-s)*1000000)
        return (datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(seconds=s,microseconds=us)).isoformat()
    return r.get('time') or 'unknown'

def verify():
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    assert json.loads((C/'catalog/current.json').read_bytes())==baseline['pointer']
    selected=json.loads((ARCHIVE/'selected-sources.json').read_bytes())
    manifest=json.loads((OUT/'passage-manifest.json').read_bytes())
    stats=json.loads((OUT/'editorial-statistics.json').read_bytes())
    ins=json.loads((OUT/'insertion-manifest.json').read_bytes())
    chapterbytes=(OUT/'01-chapter.md').read_bytes();chapter=chapterbytes.decode('utf-8')
    allbytes=(OUT/'02-new-principles.md').read_bytes();whole=allbytes.decode('utf-8')
    old=(BASE/baseline['old_manuscript']).read_bytes()
    assert sha(old)==baseline['old_manuscript_sha256']==ins['baseline_sha256']
    pos=ins['insert_at_utf8_byte'];assert old[:pos]+chapterbytes+old[pos:]==allbytes
    assert allbytes[:pos]+allbytes[pos+len(chapterbytes):]==old
    assert sha(chapterbytes)==stats['chapter_sha256']==ins['chapter_sha256']
    assert sha(allbytes)==stats['combined_sha256']==ins['combined_sha256']
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
        obj=decode(b);check_sets(obj);assert encode(obj)==b
        return obj
    for ref,r in selected.items():
        assert get(r['content'])['text']==r['text']
        assert sha(r['text'].encode())==r['text_sha256']
        o=get(r['occurrence']);assert r['content'] in [x['$link'] for x in o['content']]
        assert o['event_time']==r['native_event_time']
        for k in r['anchors']:
            anchor=get(k);assert anchor['occurrence']['$link']==r['occurrence']
    req=selected['MATH-REQUEST'];cap=req['capture'];prefix=get(cap['raw'])
    assert len(prefix)==cap['bytes'] and sha(prefix)==cap['sha256']
    native=json.loads(prefix[cap['start']:cap['end']])
    assert native['type']=='response_item' and native['payload']['role']=='user'
    texts=[b['text'] for b in native['payload']['content'] if b['type']=='input_text']
    assert texts==[req['text']] and native['timestamp']==req['time']
    units=0;total_literal=0;rebuilt='## '+manifest['title']+'\n\n'
    for x in manifest['items']:
        a,b=x['chapter_span'];p,q=x['document_span']
        assert chapter[a:b]==whole[p:q]==x['text']
        assert a==len(rebuilt)
        rebuilt+=x['text']+'\n\n'
        if x.get('ref'):
            units+=1;r=selected[x['ref']];start,end=x['source_span'];raw=r['text'][start:end]
            assert sha(raw.encode())==x['source_sha256']
            pieces=[];cursor=start
            for e in x['edits']:
                ea,eb=e['source_span'];oa,ob=e['output_span']
                assert cursor<=ea<=eb<=end
                assert r['text'][ea:eb]==e['before']
                assert x['text'][oa:ob]==e['after']
                pieces.extend([r['text'][cursor:ea],e['after']]);cursor=eb
            pieces.append(r['text'][cursor:end]);assert ''.join(pieces)==x['text']
            ops=difflib.SequenceMatcher(None,raw,x['text'],autojunk=False).get_opcodes()
            retained=sum(j-i for tag,i,j,k,l in ops if tag=='equal')
            assert retained==x['retained_characters'];total_literal+=retained
            assert sha((raw+'x').encode())!=x['source_sha256']
    assert rebuilt==chapter and units==stats['source_blocks']
    assert total_literal==stats['literal_aligned_source_characters']
    for phrase in ['我在原稿中','重新回到原稿','广东地区的基层组织的人们','精确贡献比例','受到这个系统的组织形式，以及在进化过程中对其中']:
        assert phrase not in chapter,phrase
    assert chapter.count('\n### ')==8
    assert len(re.findall('[\u3400-\u9fff]',chapter))==stats['chapter_cjk_characters']
    assert sha(chapter.replace('\n','\r\n').encode())!=stats['chapter_sha256']
    result={'schema':'mathematics-chapter.text-verification@1','status':'pass',
            'recorded_at':datetime.now(timezone.utc).isoformat(),'chapter_sha256':stats['chapter_sha256'],
            'combined_sha256':stats['combined_sha256'],'source_entries':len(selected),
            'source_units_replayed':units,'passage_units':len(manifest['items']),
            'prior_body_byte_preserved':True,'new_native_request_reparsed':True,
            'prior_sources':'CID bytes, selected texts, native time and anchor targets checked; prior native parsing accepted from expanded-edition receipt',
            'checked_source_blocks':len(checked),
            'negative_checks':['modified source fails digest','CRLF substitution fails digest'],
            'scope':'editorial text and provenance; not mathematical correctness of a new theorem, institutional effectiveness or author adoption'}
    write_json(ARCHIVE/'text-verification.json',result)
    return selected,stats,result

def sidecars(selected,stats):
    literal=stats['literal_aligned_source_characters']/stats['body_unicode_characters']
    adapted=stats['source_adapted_characters']/stats['body_unicode_characters']
    intro=f'''# 从数学家的灵感到文明的共同创造

[阅读新增章节](01-chapter.md) · [阅读接入后的《新原理》全文](02-new-principles.md) · [原话和改写对照](03-source-ledger.md) · [来源、时间与事实核对](04-sources-and-factcheck.md)

新章共 **{stats['chapter_cjk_characters']:,} 汉字**，置于“科学、教育与文明的持续创造”之后、后记之前；接入后的全文 **{stats['combined_cjk_characters']:,} 汉字**。上一版保留，正文其余部分按原字节不变。

本章从邓煜演讲提出的问题出发，用一个明确标为假想的数学协作过程，展开贡献溯源、两类资源分配、个人数据支配和动态权重网络之间的关系，再延伸到导师与学生、企业与基层创造。

正文使用 10 条此前发言及本次请求中的作者论述，共 {stats['source_blocks']} 个来源选取单元。按选取材料改写的正文字符占 {adapted:.1%}，其中逐字对齐的字符占正文 {literal:.1%}；其余为明确标注的编辑补写。这不是原创率，也不是作者已认可这些改写的证明。每处选取和改动均可逐段核对。

这是新增编辑稿。演讲中的主张、作者的制度设想、编辑构造的例子和历史事实分别处理；不把演讲者写成该制度设想的支持者。

[上一版及其完整来源索引](../2026-10-26-new-principles-expanded/00-readme.md) · [插入位置及文件校验](insertion-manifest.json) · [归档收据](09-archive-receipt.md)
'''
    (OUT/'00-readme.md').write_bytes(intro.encode())
    atlas='''# 来源、时间与事实核对

## 作者材料

下列时间是原生消息的时间，不是观点首次产生时间；较晚发言不自动构成对较早观点的撤回。混合会话只选取能辨认的作者论述，嵌入的 AI 回复不计作作者原话。正文使用第一人称是本次受托写作，不表示作者已逐句采纳编辑补写。

|原生时间（UTC）|来源|与本章的关系|
|---|---|---|
'''
    topics={'R46621':'个人数字空间、个人代理与参与能力','R46622':'AI控制权及组织权力结构','R34499':'Merkle-DAG的历史记录与回溯作用','R34488':'开放协作、贡献记录和荣誉','R34496':'动态权重作为新的组织方式','R1857':'知识的语义空间与进化空间','R34511':'公共知识基础与个人AI','R54886':'数学灵感保密、两类资源与全球思想增量','SEED-R14-0':'产品与组织同时开放','SEED-R16-0':'超越个体限制的文明智能','MATH-REQUEST':'以邓煜演讲为例展开新机制；含待核对的历史举例'}
    (OUT/'sources').mkdir(exist_ok=True)
    for ref,r in sorted(selected.items(),key=lambda pair:source_time(pair[1])):
        if ref=='MATH-REQUEST':
            (OUT/'sources/MATH-REQUEST.txt').write_bytes(r['text'].encode())
            path='sources/MATH-REQUEST.txt'
        else:path=f'../2026-10-26-new-principles-expanded/sources/{ref}.txt'
        atlas+=f'|{source_time(r)}|[{ref}]({path})|{topics[ref]}|\n'
    atlas+='''
这条材料线索从“谁掌握AI”，经过“记录知识与贡献”“动态协作”“两类资源”，到本次要求用数学案例展开。它是编辑梳理，不冒充作者逐日按照这条顺序形成全部理论。原始消息和本次完整请求仍保留，包括正文没有采用的说法。

## 外部材料

1. [《知识分子》演讲文字稿](https://zhishifenzi.com/depth/newsview/10737?category=multiple)：直接读取公开页面，正文只作简短概述。页面记载演讲发生于2026年10月25日；页面抓取时间另存，不能当作精确发表时间。没有把其中关于某AI公司的争议性叙述，改写成已经独立查证的侵权事实；本章不判断具体商业事件的责任。
2. [浙江省委党史研究室供稿的永嘉试验资料](https://www.zjzzgz.gov.cn/art/2011/4/25/art_1413013_14828112.html)：支持1956年永嘉试验和相关参与者姓名。正文采用这个有记录的例子，不采用“广东最早”的断言，也不另行宣布全国唯一最早。
3. [邓小平纪念网所载谈话记录](https://cpc.people.com.cn/n1/2018/0703/c69113-30107101.html)：支持1980年5月31日谈话肯定肥西、凤阳实践。它是刊载谈话的回顾文章，并非本轮取得的原始录音或手稿。

资料存在对基层参与者的记载，所以不写“完全没有获得承认”。如何衡量荣誉是否公平，是本章分析的问题，不能仅由这些史料直接算出。各类贡献之间的机制类比，也不是对具体导师、企业负责人或政治人物的侵占指控。

## 关键编辑边界

- 保留“囚徒困境式的局部最优”作为解释合作障碍的类比；未建立具体支付矩阵，不称已证明全局最优或纳什均衡。
- 原话中“精确贡献值”展开为可核对的贡献记录及具体评价，避免将代码行数、提交次数或哈希值视为客观的唯一价值尺度。原句仍可在对照中检查。
- 个人需求、公共资源、专业判断的参考权重分别讨论；参考权重不等于基本权利、材料授权或历史贡献份额。
- 假想研究过程不是已发生的发现；具身的文明智能是作者设想，不写成当前已部署能力。
- 来源追溯不能被扩张成万能训练归因；公众的知识共享也不等于强制公开个人生活。
- “一切开源”的方向保留，补上个人材料选择、可审查规则和不同方法并行的具体含义。

所有实质性润色均为本次编辑建议。它们可以接受作者进一步修订，不在知识库中登记为作者已经改变立场。
'''
    (OUT/'04-sources-and-factcheck.md').write_bytes(atlas.encode())
    plan={'schema':'mathematics-chapter.semantic-plan@1','new_concept':{'label':'从数学灵感到共同创造的贡献链','definition':'以未完成灵感进入可追溯的协作网络为例，分析信息共享、贡献承认、个人需求保障、公共资源安排和AI共同治理如何相互支持；属于作者方案的编辑展开。'},
          'relations':[
            {'concept':'C13','section':'三','refs':['R34499','R34488'],'scope':'内容与版本记录帮助核对贡献来源，不独自证明思想首创'},
            {'concept':'C14','section':'二、三','refs':['R1857','R46621'],'scope':'个人知识的语义与演化结构为研究过程提供来源'},
            {'concept':'C22','section':'六','refs':['SEED-R16-0'],'scope':'文明智能为跨个体协作的远期设想'},
            {'concept':'C23','section':'六','refs':['R34496','R34511','R46622'],'scope':'动态领域权重用于相关问题判断与反馈'},
            {'concept':'C25','section':'五','refs':['R54886','R34488'],'scope':'个人需要与公共研究资源分离，改变封闭动机'},
            {'concept':'C26','section':'三、六、七','refs':['SEED-R14-0','R34488'],'scope':'开放组织与共同生产用于工具控制和贡献承认'},
            {'concept':'C27','section':'三','refs':['R46621','SEED-R14-0'],'scope':'研究材料的支配与用途选择'},
            {'concept':'C31','section':'四、七','refs':['MATH-REQUEST','R54886'],'scope':'灵感经接续、反例、验证成为知识增量的假想例子'},
            {'concept':'C32','section':'一、五、八','refs':['MATH-REQUEST','R54886','R34488'],'scope':'信息共享的合作条件；未证明全局最优'}],
          'basis':'editorial application of prior concepts at author request; not independent validation or author adoption'}
    write_json(ARCHIVE/'semantic-plan.json',plan)
    profile='''# 数学案例章节归档说明

沿用 PKST 0.1 和 PKST-CBOR-1。结构对象命名空间 math=urn:pkst:editorial:mathematics-contribution:1。

本轮新增一个原生用户请求，复用10条既有消息的身份、正文与锚。原生通道为user不自动确认为human；引文holder保持unknown，人工归属判断另存于段落。正文属于编辑提案，不等于作者采纳。全部保存在本机。

math/document@1 保存完整新版、上一版及新章字节；math/passage@1 保存有序段落、引文、来源及改动；math/source@1 指向已有原生消息和取证锚；math/web-evidence@1 保存公开来源URL及有限事实观察，网页抓取另标原始HTML或派生阅读投影；math/source-timepoint@1 使用原生时间，不倒填思想起源。所有数组除协议保留的集合字段外均有序。

复制旧SQLite视图到独立目录，追加新集合并核对引用闭包及无环。只有文本重放、版本插入、原件身份和归档复核通过后，才比较旧指针并切换当前目录。旧原件、旧正文、旧目录不覆盖。结构核验不认证理论真理、现实制度效能或作者同意。

构造取舍：直接覆盖旧稿会丢失版本边界；只存散文缺少逐段来源；本轮采用独立章节、字节插入清单、既有对象复用及一次有界目录增量。不增加独立服务或重新分析全部语料，不作性能或能耗优势承诺。
'''
    (ARCHIVE/'PROFILE.md').write_bytes(profile.encode())
    webmeta=json.loads((WORK/'web-capture.json').read_bytes())
    write_json(ARCHIVE/'external-sources.json',[
        {'id':'speech','title':'邓煜演讲文字稿','url':webmeta['url'],'access':'direct HTTPS public HTML','capture':webmeta,'html_file':'speech-page.html','reading_projection':'speech-reading.txt','claim':'作者肯定AI数学进展，强调贡献追溯、使用选择与人的主体性；演讲发生于2026-10-25','boundary':'report of speech, not independent substantiation of alleged company conduct'},
        {'id':'yongjia','title':'永嘉包产到户的探索和实践','url':'https://www.zjzzgz.gov.cn/art/2011/4/25/art_1413013_14828112.html','access':'web tool public page','observed_on':'2026-10-26','claim':'1956年永嘉试验；相关参与者李桂茂、李云河、戴洁天','boundary':'does not quantify fairness of honor or establish Guangdong as first'},
        {'id':'deng-policy','title':'历史选择了邓小平（55）','url':'https://cpc.people.com.cn/n1/2018/0703/c69113-30107101.html','access':'web tool public page','observed_on':'2026-10-26','claim':'1980-05-31谈话肯定肥西和凤阳实践','boundary':'retrospective publication containing speech, not original recording'}])

if __name__=='__main__':
    selected,stats,result=verify();sidecars(selected,stats)
    print(json.dumps(result,ensure_ascii=False))
