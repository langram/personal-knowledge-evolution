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
    req=selected['INTELLIGENCE-REQUEST'];cap=req['capture'];prefix=get(cap['raw'])
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
    for unwanted in ['萧伯纳也说过','智能的复制成本几乎为零的时代已经不远了','我在原稿中','重新回到原稿']:
        assert unwanted not in chapter
    assert sha(chapter.replace('\n','\r\n').encode())!=stats['chapter_sha256']
    result={'schema':'pi/text-verification@1','status':'pass','recorded_at':datetime.now(timezone.utc).isoformat(),
            'chapter_sha256':stats['chapter_sha256'],'combined_sha256':stats['combined_sha256'],
            'source_entries':len(selected),'source_units_replayed':units,'passage_units':len(man['items']),
            'previous_passages_byte_preserved':len(old_units),'all_previous_body_units_preserved':True,
            'outside_chapter_byte_preserved':True,'new_request_reparsed':True,'checked_source_blocks':len(checked),
            'prior_sources':'selected immutable content, native time and anchor targets checked; original parsing relies on preceding receipts',
            'negative_checks':['source mutation changes digest','CRLF substitution changes digest'],
            'scope':'editorial text/provenance; not institutional validation or author acceptance of all edits'}
    write_json(ARCHIVE/'text-verification.json',result);db.close()
    return selected,stats,result
def sidecars(selected,stats):
    (OUT/'sources').mkdir(exist_ok=True)
    (OUT/'sources/INTELLIGENCE-REQUEST.txt').write_bytes(selected['INTELLIGENCE-REQUEST']['text'].encode())
    total=stats['body_unicode_characters'];adapt=stats['source_adapted_characters']/total;literal=stats['literal_aligned_source_characters']/total
    readme=f'''# 从数学家的灵感到文明的共同创造 融合修订版

[阅读全文](01-chapter.md) · [《新原理》完整合订稿](02-new-principles.md) · [原话和改写对照](03-source-ledger.md) · [来源与编辑说明](04-sources-and-editing.md)

本章现为 **{stats['chapter_cjk_characters']:,} 汉字**，全文 **{stats['combined_cjk_characters']:,} 汉字**。本次把作者关于知识与智能、知识共享历史、公共智能及其组织机制的论述，融合到数学案例的推理过程中。

新增第二至第四节：知识与智能怎样相互生成；从知识共享到智能共享；共同的智能需要怎样的共同组织。后面的数学研究过程也接上了知识进入公共智能、再支持下一轮创造的循环。原章全部正文单元保留，部分段落移动；节标题重新编号。全书其他章节按原字节保留。

沿用11个来源入口，新增本次作者发言1条。37个来源选取单元保留原话和逐项改写；来源改写字符占正文 {adapt:.1%}，逐字对齐的来源字符占正文 {literal:.1%}。这两项都不是作者原创率，来源改写也不全是标点润色。补写和实质性修订在对照中单独可见。

[上一版](../2026-10-26-mathematics-and-contribution/00-readme.md) · [章节替换清单](replacement-manifest.json) · [段落移动记录](reorganization.json) · [归档收据](09-archive-receipt.md)
'''
    (OUT/'00-readme.md').write_bytes(readme.encode())
    note='''# 来源与编辑说明

## 这次融合的主线

知识可以积累和传播；智能使已有知识被运用、检验并产生新知识。文字、印刷和数字网络扩大知识共享，模型的可复制和可部署又为能力共享提供新条件。作者由此提出公共智能的制度主张，并把开放范围扩展到数据、训练、运行、反馈、决策和贡献分配。数学案例用来说明这一循环如何具体展开。

新的论述来自[本次作者原话](sources/INTELLIGENCE-REQUEST.txt)。开头“写得不错”的正面反馈也保留，但没有解释成对上一版每一句技术、历史或编辑判断的逐项批准。

## 保留和调整

- 原章正文单元全部逐字保留，涉及开源协作、AI控制权和开放组织的部分移入新章节。旧稿不覆盖，全书其他章节按字节不变。
- 尽量保留“智能是产生新知识的机制、能力和过程”“知识和智能相互促进”“阳光和空气”“人类智力集成系统”“整个文明智能体”等原有表达，并为循环和组织之间补出衔接。
- 存在与变化、对象与态射、物质和能量、波与粒子等，作为跨领域观察的线索；不写成这些概念已被证明同构或可以直接互换。
- “基本智能服务免费”保留为作者的制度目标，说明成本由共同体承担。模型复制不必重做全部训练，但运行消耗硬件、能源、存储、通信和维护，不能由复制成本直接推出无限免费运行。
- “全生命周期公共”落实为共同规则、公共资源、公共研究与可审查运行记录；不将个人私密材料自动公开，也不把作者身份、使用授权和公共决策权混成同一种权利。
- “所有知识都在模型里”调整为从大量材料学习规律的模型，加上知识库、检验工具、人和现实反馈。模型不作为完整、无误的人类知识副本。
- 对“知识中的大部分已开源”“当前商业安排必然整体低效”等范围过大的判断，保留方向，收窄量化或因果断言。没有据此宣布作者撤回原观点；原句与改句均在逐段对照中。

## 引语与外部资料

|来源|使用范围|核对结果|
|---|---|---|
|[杰斐逊致麦克弗森，1813-08-13](https://monadnock.net/jefferson/mcpherson.html)|蜡烛传光的思想传播比喻|书信确有此比喻，正文意译；不据此把杰斐逊全部专利立场等同于作者主张。此处读取的是公开转录，不是手稿。|
|[苹果与思想比喻的出处考察](https://quoteinvestigator.com/2011/12/13/swap-ideas/)|判断能否署名萧伯纳|未发现有力的萧伯纳出处，保留用户提供的通行比喻而不署其名；不另行宣布一个确定原创者。|
|[GNU最初公告](https://www.gnu.org/gnu/initial-announcement.html)|1983年项目公告与共享理念|使用GNU官方文本；自由软件运动与后来使用“开源”名称的运动不混作同一历史起点。|
|[GNU关于自由软件与收费](https://www.gnu.org/philosophy/selling.en.html)|自由和价格的区别|使用官方说明；本文基本智能服务免费是作者进一步的制度主张，不归给斯托曼。|
|[AI部署能耗研究，v3](https://arxiv.org/abs/2311.16863v3)|实际推理具有运行成本|使用作者原始研究；不从特定实验推算本方案当前成本，不声称所有任务都同等耗能。|

GNU两页的直接HTML保存返回403，已保留失败状态；相关论断依据本轮网页工具返回的官方内容。其余列入抓取清单的页面保存了公开HTML。抓取时间、发表时间和历史事件时间分别处理。没有把抓取到的完整第三方文章放进读者正文。

此前数学演讲及农村改革的来源继续沿用[上一版核对说明](../2026-10-26-mathematics-and-contribution/04-sources-and-factcheck.md)。

## 本版材料时间线

时间仅表示消息发生时间，不是理论最早产生时间。新补充作为新的来源事件，不倒填到此前会话。新增的概念联系由Codex作编辑解释，不登记为制度已经得到验证。

|原生时间（UTC）|材料|用途|
|---|---|---|
'''
    for ref,r in sorted(selected.items(),key=lambda p:time_display(p[1])):
        if ref=='INTELLIGENCE-REQUEST':path='sources/INTELLIGENCE-REQUEST.txt';usage='本次知识与智能及公共基础设施论述'
        elif ref=='MATH-REQUEST':path='../2026-10-26-mathematics-and-contribution/sources/MATH-REQUEST.txt';usage='此前数学案例写作请求'
        else:path=f'../2026-10-26-new-principles-expanded/sources/{ref}.txt';usage='沿用此前论述及选取区间'
        note+=f'|{time_display(r)}|[{ref}]({path})|{usage}|\n'
    (OUT/'04-sources-and-editing.md').write_bytes(note.encode())
    profile='''# 公共智能论述融合归档

沿用PKST 0.1与PKST-CBOR-1。pi命名空间为urn:pkst:editorial:public-intelligence:1。新增一个原生发言，复用11个此前来源。user通道不自动等于human归属，供稿里的引语不自动等于作者原创。

pi/document@1连接新全文、前全文和章节替换清单；pi/passage@1按阅读顺序保存段落及来源改写，并以previous_passage连接保留的上一版段落；pi/chapter@1保存本章；pi/source@1与pi/source-timepoint@1保留原生消息和时间；pi/web-evidence@1区分原始HTML、网页工具阅读依据、失败抓取和解释性来源说明。除协议保留的集合字段外数组有序。

结构归档不等于作者逐句采纳，也不证明社会方案有效。当前赞许按具体消息保存，不扩大为全面采纳。档案本地保存，历史正文与目录不覆盖。

本轮复用已有编解码和有界索引方式，在新SQLite视图中追加集合，完成引用和内容重放后才切换指针。没有引入新服务或重新解析全库。目录副本约1.4GB，是现有索引方式的存储成本，不称为最优压缩或能耗收益。
'''
    (ARCHIVE/'PROFILE.md').write_bytes(profile.encode())
    plan={'schema':'pi/semantic-plan@1','new_concept':{'label':'知识与智能的相互生成及公共智能基础设施','definition':'知识积累支持智能能力形成，智能经实践和检验产生新知识；作者主张将基本智能能力及其公共治理作为共同基础设施。模型可复制是条件，不自动消除运行成本或决定制度选择。'},
          'relations':[
            {'concept':'C12','section':'二、三','refs':['INTELLIGENCE-REQUEST'],'scope':'公共知识经学习支持能力形成，研究结果再进入公共知识'},
            {'concept':'C13','section':'六、七','refs':['INTELLIGENCE-REQUEST','R34499'],'scope':'内容与演化记录为公共智能全过程的可核验关系提供基础'},
            {'concept':'C22','section':'四、九','refs':['INTELLIGENCE-REQUEST','SEED-R16-0'],'scope':'由人、模型、工具和现实反馈连接的文明智能设想'},
            {'concept':'C23','section':'四、九','refs':['INTELLIGENCE-REQUEST','R34511'],'scope':'共同规则及动态权重参与公共资源决策'},
            {'concept':'C25','section':'三、八','refs':['INTELLIGENCE-REQUEST','R54886'],'scope':'基本智能服务与公共算力配置联系；免费使用不等于无物理成本'},
            {'concept':'C26','section':'四','refs':['INTELLIGENCE-REQUEST','SEED-R14-0'],'scope':'开放由产品扩展至组织、运行和决策机制'},
            {'concept':'C27','section':'四、六','refs':['INTELLIGENCE-REQUEST','R46621'],'scope':'个人数据支配与公共智能共享的兼容边界'},
            {'concept':'C31','section':'七','refs':['INTELLIGENCE-REQUEST','MATH-REQUEST'],'scope':'数学创新进入公共能力形成与下一轮研究的循环'},
            {'concept':'C32','section':'一、四','refs':['INTELLIGENCE-REQUEST','R54886'],'scope':'减少信息封闭的合作条件，不据此断言已达全局最优'}],
          'previous_case_relation':'new concept explains institutional context of previous mathematics case; not a replacement or retraction',
          'basis':'editorial consolidation requested by author; not empirical verification'}
    write_json(ARCHIVE/'semantic-plan.json',plan)
    captures={r['id']:r for r in json.loads((WORK/'web-captures.json').read_bytes())}
    external=[
        {'id':'jefferson','title':'Jefferson to Isaac McPherson, 13 August 1813','claim':'Ideas and candle-light sharing analogy; no zero-cost AI claim'},
        {'id':'quotation-attribution','title':'Apple and idea quotation provenance investigation','claim':'No compelling Shaw attribution located; no definite origin asserted by this edition'},
        {'id':'gnu-initial','title':'GNU Initial Announcement','claim':'1983 announcement and software sharing intention'},
        {'id':'gnu-selling','title':'Selling Free Software','claim':'Freedom and price are distinct; free software can be sold'},
        {'id':'inference-energy','title':'Power Hungry Processing v3','claim':'Inference deployment has measurable energy cost; no local cost estimate derived'}]
    for x in external:
        x['capture']=captures[x['id']];x['url']=x['capture']['url']
        x['access']='public HTML capture and web tool reading' if x['capture']['status']=='captured' else 'web tool returned official page content; direct HTML capture failed'
    write_json(ARCHIVE/'external-sources.json',external)
if __name__=='__main__':
    selected,stats,result=verify();sidecars(selected,stats);print(json.dumps(result,ensure_ascii=False))
