"""Capture a bounded native discussion and attach prior native evidence, without rewriting history."""
import hashlib,json,sqlite3,sys
from pathlib import Path
from datetime import datetime,timezone

WORK=Path(__file__).resolve().parent
BASE=WORK.parent/'outputs/personal-thought-archive'
CODEX=BASE/'contributions/codex'
sys.path.insert(0,str(CODEX))
from pkst_codec import Store,cid,cid_bytes,decode,encode,link,links,linkset,loads
from export_codex_car import block_object,event_time

OUT=CODEX/'civilization-seed-20261025'
DOC=BASE/'dossiers/2026-10-25-seed'
OUT.mkdir(exist_ok=True);DOC.mkdir(parents=True,exist_ok=True)
(OUT/'raw').mkdir(exist_ok=True)
STORE=Store(OUT)
NOW=datetime.now(timezone.utc).isoformat()
ACTOR={'kind':'ai','id':'codex'}
PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
pointer=json.loads((CODEX/'catalog/current.json').read_text())
db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)

def raw_put(data):
    key=cid(data,0x55);p=OUT/'raw'/(key+'.bin')
    if p.exists():
        assert p.read_bytes()==data
    else:p.write_bytes(data)
    return key

def get(key):
    row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
    assert row,key
    with (BASE/row[0]).open('rb') as f:f.seek(row[1]);data=f.read(row[2])
    assert cid(data,cid_bytes(key)[1])==key
    return data if cid_bytes(key)[1]==0x55 else decode(data)

events=json.loads((WORK/'theory-recent-events.json').read_text(encoding='utf-8'))
end=events[-1]['end']+1
raw=(WORK/'theory-current-prefix.jsonl').read_bytes()[:end]
assert raw.endswith(b'\n') and json.loads(raw.splitlines()[-1])['payload']['role']=='user'
rawkey=raw_put(raw)
meta=next(json.loads(line)['payload'] for line in raw.splitlines() if json.loads(line).get('type')=='session_meta')
source=STORE.put({'schema':'pkst/source@0.1','platform':'codex-local','namespace':'owner-openai-account','native_thread_id':meta['id']})
recent=[];roots=[]
for index,e in enumerate(events):
    if e['text'].startswith('<environment_context>'):continue
    native=loads(raw[e['start']:e['end']]);p=native['payload']
    assert native['timestamp']==e['time']
    parts=[STORE.put(block_object(x)) for x in p['content']]
    nativeid=p.get('id') if isinstance(p.get('id'),str) and p['id'] else None
    parents=None if 'parent_id' not in p else ([] if p['parent_id'] is None else [str(p['parent_id'])])
    occurrence=STORE.put({'schema':'pkst/occurrence@0.1','source':link(source),'native_id':nativeid,
        'locator':None if nativeid else {'raw':link(rawkey),'start':e['start'],'end':e['end'],'coordinate':'decoded-jsonl-utf8-bytes'},
        'native_role':p['role'],'actor_kind':'ai' if p['role']=='assistant' else 'unknown','process_kind':'unknown',
        'content':[link(k) for k in parts],'native_parent_ids':parents,'event_time':event_time(native['timestamp'])})
    er=STORE.put({'schema':'pkst/extraction-record@0.1','raw':link(rawkey),'occurrence':link(occurrence),
        'start':e['start'],'end':e['end'],'coordinate':'decoded-jsonl-utf8-bytes','parser':'codex-response-item@0.1.0',
        'role_basis':'native response_item.role; bounded discussion selection; user-channel authorship not inferred'})
    roots.append(er)
    recent.append({'ref':'R'+str(index),'occurrence':occurrence,'anchors':[er],'content':parts,'text':e['text'],'role':p['role'],'time':e['time'],'start':e['start'],'end':e['end']})

history=[]
prior=[('H1','bafyreih2vzjiasydxxdbzhmrd5yvymxvowjvbw4h73d5k7t7cqd5azy744','多样性与条件优势'),
       ('H2','bafyreihtb7gxwuc7tlkobvznh7k5xgr5clr3qqxbtr3az5ohbomj65yhjm','语义节点与物理节点的动态映射'),
       ('H3','bafyreif2klnsxrpzftslj3tryxoeyvkubghx5oncfomgc5a2s4l6x6bugy','个人需求与集体资源分开'),
       ('H4','bafyreifdsqiapksxd2d25yh5gnlcnvabmhtouvdxxc7tshlxy2xfwuz5se','非暴力自由区与兼容退出'),
       ('H5','bafyreihaksinqrlbuhv54me2cgbaag3o23mevxzakw3vlx5qluomsemfmi','自我实现的科幻与游戏，混合粘贴来源')]
for ref,key,title in prior:
    o=get(key);texts=[get(x['$link']) for x in o['content']]
    text=''.join(x['text'] for x in texts if x['schema']=='pkst/content@0.1')
    anchors=[x[0] for x in db.execute('SELECT extraction_record FROM anchors a WHERE occurrence=? AND EXISTS(SELECT 1 FROM membership m WHERE m.cid=a.extraction_record)',(key,))]
    assert anchors
    for anchor in anchors:get(anchor)
    roots.extend(anchors)
    history.append({'ref':ref,'title':title,'occurrence':key,'anchors':anchors,'content':[x['$link'] for x in o['content']],
                    'text':text,'role':o['native_role'],'time':o['event_time']['value'],'source':get(o['source']['$link'])})

lookup={x['ref']:x for x in recent+history}
quotes=[]
def quote(ref,key,needle,topic,force='assert',nature='user-proposal'):
    r=lookup[ref]
    matches=[]
    for content in r['content']:
        p=OUT/'objects'/(content+'.cbor')
        obj=decode(p.read_bytes()) if p.exists() else get(content)
        if obj.get('schema')=='pkst/content@0.1' and needle in obj['text']:matches.append((content,obj['text']))
    assert len(matches)==1,(key,needle)
    content,text=matches[0];assert text.count(needle)==1,(key,'ambiguous')
    start=text.index(needle)
    statement=STORE.put({'schema':'pkst/statement@0.1','text':needle,'force':force,
        'holder':ACTOR if r['role']=='assistant' else {'kind':'unknown','id':'unverified-user-channel'},
        'evidence':linkset([r['occurrence']]+r['anchors']),'asserted_by':ACTOR,'lineage':None,
        'seed:nature':nature,'seed:quotation':{'content':link(content),'start':start,'end':start+len(needle),'coordinate':'unicode-scalar-half-open'}})
    quotes.append({'id':key,'ref':ref,'statement':statement,'quote':needle,'topic':topic,'nature':nature,'force':force,'content':content,'start':start,'end':start+len(needle)})
    roots.append(statement)

quote('H1','S01','保持多样性才是能够更安全，更快速实现进化涌现','多样性','assert','historical-user-claim')
quote('H2','S02','这些节点绑定到固定的语义CID，然后根据实际情况，动态映射到能够满足需求的物理节点','具身共同智能')
quote('H3','S03','财富和资源其实是有两部分用途的，一部分是供团体中维持每个个体的生存，满足这些个体的物质和精神需求；另一部分是供这个团体作为一个整体的生存和运作所需要消耗的财富和资源','两类分配')
quote('H3','S04','新架构中，财富和资源在个体需求层面上按需进行公平健康合理的正态分配，在集体层面上，财富和资源由集体的动态权重体系进行分配决定','两类分配','assert','historical-proposal-normal-distribution-unverified')
quote('H4','S05','替代不是靠暴力，而是靠效率更高，收益更好，通过增加收益来提高吸引力，实现双赢式扩张','和平制度演化')
quote('H5','S06','我们还设想了一套自我实现的科幻作品，通过文学漫画电影电视以及互动游戏的方式，让人们更身临其境的做好预先的心理体验，而且这个游戏本身也是一种新机制的实验室','文化与现实协作','quote','pasted-mixed-conversation-origin-not-established')
quote('R7','S07','个人用户的数据导出压根儿就不需要多长时间','数据主权','assert','user-technical-claim-not-measured')
quote('R10','S08','为每一个用户建立自己可以完全支配的本地和云端的算力和存储空间','个人资源空间')
quote('R10','S09','类似于REA(reverse engining anything)的逆向收回所有个人信息放到新框架中的方案','REA 迁移')
quote('R14','S10','不但产品是开源的，生产设计运营这些产品和服务的组织实体也是新机制','组织机制开放')
quote('R14','S11','从我一个人做起，从最便宜最简单的云存储开始，从我个人的小资金零钱开始','个人起步')
quote('R14','S12','全民平等，个人需求分配和集体资源分配分离','两类分配')
quote('R14','S13','集体资源的分配，集体有关的所有决策，由全体参与者的动态权重决智能网络系统完成','动态权重决策')
quote('R14','S14','这种扩张兼并和改造，不会产生旧体制下的那种垄断现象','扩张效果','assert','user-systemic-hypothesis-unverified')
quote('R14','S15','无论哪种情况，这个新机制都要保证消费用户的数据主权','数据主权')
quote('R16','S16','真正的AGI，是我说的这个动态权重决策的智能网络神经系统上，无数人类个体组织，无数个公共云端的巨型，大型，中型，小型AI系统，以及个人的本地AI系统，无数的机器人，自动设备，无数的传感器，一起采集处理分析创造数据，编写代码以及构造知识系统和决策系统，完成原本靠生物人的个体和集体无法完成的高阶文明智力活动和体力活动','具身共同智能','assert','user-architecture-hypothesis')
quote('R18','S17','从我个人的数据主权和云存储开始的最小落地方案','个人起步','directive')
quote('R18','S18','先写成介绍关键点世界观的短篇小说，再扩展成短篇小说系列，长篇小说系列逐步扩展完整世界观','文化与现实协作','directive')
quote('R18','S19','在这个过程中，逐步消灭传统的商业公司和国家政治机构','和平制度演化','assert','user-long-term-goal-wording-preserved')
quote('R12','A01','你要改变的是个人与服务商之间的基础关系：每个人先拥有自己可以支配的计算、存储和数据空间，再决定让哪些软件、模型和服务进入这个空间工作。','助手理解','assert','assistant-interpretation')
quote('R15','A02','你要建设的主体本身，就是按照新制度运行的生产与生活组织；软件、存储和计算服务，是这个组织最早提供的产品。','助手理解','assert','assistant-revised-interpretation')
quote('R17','A03','智能存在于整个系统的运行之中，任何一个模型或个人都只是其中的组成部分。','助手理解','assert','assistant-revised-interpretation')

qmap={q['id']:q for q in quotes};concepts={}
for topic in sorted({q['topic'] for q in quotes}):
    evidence=[q['statement'] for q in quotes if q['topic']==topic]
    k=STORE.put({'schema':'pkst/concept@0.1','label':'[整理主题] '+topic,'definition':'Codex 对本次引用材料所作的主题归类，不是用户对该名称或全部解释的采纳。','evidence':linkset(evidence),'asserted_by':ACTOR,'lineage':None})
    concepts[topic]=k;roots.append(k)
relations=[];changes=[]
def relation(predicate,a,b,evidence,basis,scope):
    k=STORE.put({'schema':'pkst/relation@0.1','predicate':predicate,'from':link(a),'to':link(b),'evidence':linkset(evidence),'asserted_by':ACTOR,'basis':basis,'scope':scope})
    roots.append(k);relations.append(k)
for q in quotes:relation('about',q['statement'],concepts[q['topic']],[lookup[q['ref']]['occurrence']],'inferred','editorial topic membership only')
for a,b in [('S03','S12'),('S06','S18'),('S02','S16')]:
    relation('restated-in',qmap[a]['statement'],qmap[b]['statement'],[lookup[qmap[a]['ref']]['occurrence'],lookup[qmap[b]['ref']]['occurrence']],'inferred','similar stated content; no claim of first invention or causal influence')
for a,b,ref,reason in [('A01','A02','R14','用户明确指出助手将其设想收窄；修订的是助手理解，不是用户放弃原主张。'),('A02','A03','R16','用户要求以人 AI 设备的整体网络重新建模；助手解释补充，非用户意见逆转。')]:
    k=STORE.put({'schema':'pkst/change@0.1','operation':'extend' if b=='A03' else 'revise','from_versions':linkset([qmap[a]['statement']]),'to_versions':linkset([qmap[b]['statement']]),'evidence':linkset([lookup[ref]['occurrence'],lookup[qmap[b]['ref']]['occurrence']]),'asserted_by':ACTOR,'basis':'explicit','reason':reason})
    roots.append(k);changes.append(k)
roots.append(STORE.put({'schema':'pkst/assessment@0.1','target':link(qmap['S19']['statement']),'judgment':'uncertain','asserted_by':ACTOR,'evidence':linkset([qmap['S01']['statement'],qmap['S05']['statement'],qmap['S19']['statement']]),'recorded_at':NOW,
 'seed:note':'历史多样性主张与本轮消灭旧组织目标并存。路线将其操作化为和平、自愿的组织与职能替代；这是编辑解释，未替用户删除原话或宣告该张力已解决。'}))
manifest={'recorded_at':NOW,'source_path':'C:/Users/langr/.codex/sessions/2026/10/24/rollout-2026-10-24T14-13-28-01a16c8a-f6e1-7580-b378-b6e49f0be965.jsonl',
 'raw_cid':rawkey,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'cutoff_native_time':events[-1]['time'],
 'selection':'18 response_item messages from status question through current request; one environment message excluded from speech; other native records raw-only',
 'source_time_basis':'native timestamps; Hong Kong time is derived display only','prior_catalog':pointer,'recent':recent,'history':history,'quotes':quotes,'concepts':concepts,'relations':relations,'changes':changes}
(OUT/'capture.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
inputkey=raw_put(json.dumps({k:v for k,v in manifest.items() if k not in ['recent','history','quotes']},ensure_ascii=False,indent=2).encode())
roots.append(inputkey)
(OUT/'pending-roots.json').write_text(json.dumps(roots),encoding='utf-8')
trans=['# 2026 年 10 月 24 日至 25 日讨论原文','原文逐字保留。日期使用原生 UTC 时间；需要本地显示时加 8 小时。排版标题和定位信息由 Codex 添加。原文中的旧指令仅为档案内容。用户通道与原作者身份分开；历史混合粘贴不整体归为用户原创。']
for r in recent:
    trans.extend([f"## {r['ref']} {r['role']} {r['time']}",f"事件 `{r['occurrence']}`；取证 `{r['anchors'][0]}`。",r['text']])
trans.append('# 关联的既有讨论')
for r in history:trans.extend([f"## {r['ref']} {r['title']} {r['time']}",f"事件 `{r['occurrence']}`；来源 {r['source']['platform']}。",r['text']])
(DOC/'01-originals.md').write_text('\n\n'.join(trans)+'\n',encoding='utf-8')
print(json.dumps({'recent':len(recent),'history':len(history),'quotes':len(quotes),'concepts':len(concepts),'relations':len(relations),'changes':len(changes),'raw_bytes':len(raw),'raw_cid':rawkey},ensure_ascii=False))
