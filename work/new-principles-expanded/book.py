"""Source-led manuscript assembly. Raw sources are never altered."""
import difflib, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from sources import sources, paragraphs, ROOT, WORK, BASE

OUT=BASE/'dossiers/2026-10-26-new-principles-expanded'
DATA=sources()
PLAN=[
('00','前言：为什么要重新考察数学、科学与文明'),
('01','极限、悖论与认识的边界'),
('02','存在、变化与可构造性'),
('03','不动点、最小化、最大化与涌现'),
('04','物理世界与层层构造的自然'),
('05','意识、信息与自我驱动的智能'),
('06','合作、冲突与社会结构的形成'),
('07','机器、人工智能与平等的物质条件'),
('08','语言、公共知识与文明的共同记忆'),
('09','个人知识的语义空间与时间线'),
('10','从反复思考到可以复用的能力'),
('11','新语言、Structoken 与 FPM'),
('12','MerkleVM 与可以生长的软件种子'),
('13','人和 AI 怎样共同研究与构造'),
('14','具有感官与行动能力的文明智能'),
('15','动态权重的社会神经网络'),
('16','个人需求与集体资源的两种分配'),
('17','产品、组织与决策的全面开放'),
('18','个人数据主权、隐私与公共知识'),
('19','从一个人的云存储开始'),
('20','自由区的生长与制度的和平演化'),
('21','自我实现的科幻与文化建设'),
('22','科学、教育与文明的持续创造'),
('23','后记：让每一个人都成为创造者'),
]

def norm(t):
    return re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+','\n\n',t.replace('\r','')).strip()

class Chapter:
    def __init__(self,key):
        self.key=str(key).zfill(2);self.title=dict(PLAN)[self.key];self.items=[]
    def add(self,text,reason='衔接、展开或例证'):
        self.items.append({'kind':'editorial-addition','text':norm(text),'reason':reason})
    def heading(self,text):self.add('### '+text,'节标题')
    def polish(self,pairs):
        for old,new in pairs:
            hits=[x for x in self.items if old in x['text']]
            if len(hits)!=1 or hits[0]['text'].count(old)!=1:
                raise ValueError(('polish must match exactly once',self.key,old))
            item=hits[0];item['text']=item['text'].replace(old,new)
            if item.get('ref'):
                a,b=item['source_span'];raw=DATA[item['ref']]['text'][a:b];text=item['text']
                ops=difflib.SequenceMatcher(None,raw,text,autojunk=False).get_opcodes()
                item['kind']='source-adaptation'
                item['edits']=[{'operation':tag,'source_span':[a+i,a+j],'output_span':[k,l],'before':raw[i:j],'after':text[k:l]} for tag,i,j,k,l in ops if tag!='equal']
                item['retained_characters']=sum(j-i for tag,i,j,k,l in ops if tag=='equal')
    def src(self,ref,first=None,last=None,*,start=None,end=None,replacements=(),note='作者发言；已人工区分嵌入的 AI 回复'):
        r=DATA[ref];p=paragraphs(r['text']);a=0 if first is None else p[first]['start'];b=len(r['text']) if first is None else p[first if last is None else last]['end']
        if start is not None:
            a=r['text'].index(start,a,b)
        if end is not None:
            b=r['text'].index(end,a,b)+len(end)
        raw=r['text'][a:b];text=norm(raw)
        for old,new in replacements:
            if old not in text:raise ValueError((ref,'replacement not found',old))
            text=text.replace(old,new)
        # Count only literal characters retained by explicit, reviewable alignment.
        ops=difflib.SequenceMatcher(None,raw,text,autojunk=False).get_opcodes()
        self.items.append({'kind':'source-adaptation' if raw!=text else 'source-exact','ref':ref,'source_span':[a,b],'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'text':text,'edits':[{'operation':tag,'source_span':[a+i,a+j],'output_span':[k,l],'before':raw[i:j],'after':text[k:l]} for tag,i,j,k,l in ops if tag!='equal'],'retained_characters':sum(j-i for tag,i,j,k,l in ops if tag=='equal'),'author_assessment':note})
    def save(self,review):
        folder=WORK/'chapters';folder.mkdir(parents=True,exist_ok=True)
        x={'chapter':self.key,'title':self.title,'status':'draft-reviewed','review':review,'items':self.items}
        (folder/(self.key+'.json')).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
        build()

def build():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'chapters').mkdir(exist_ok=True)
    chapters=[];manifest=[];whole='# 新原理：现代科学与人类文明的构造\n\n';sources_used={}
    for key,title in PLAN:
        f=WORK/'chapters'/f'{key}.json'
        if not f.exists():continue
        c=json.loads(f.read_text(encoding='utf-8'));chapter_text='## '+title+'\n\n';prefix=len(whole);items=[]
        for ref in c.get('review',{}).get('evidence_refs',[]):
            sources_used[ref]=DATA[ref]
        for item in c['items']:
            item=dict(item);item['chapter_span']=[len(chapter_text),len(chapter_text)+len(item['text'])];item['document_span']=[prefix+x for x in item['chapter_span']]
            chapter_text+=item['text']+'\n\n';items.append(item)
            if item.get('ref'):sources_used[item['ref']]=DATA[item['ref']]
        path=OUT/'chapters'/f'{key}.md';path.write_bytes(chapter_text.encode('utf-8'))
        whole+=chapter_text
        cjk=len(re.findall(r'[\u3400-\u9fff]',chapter_text));retained=sum(x.get('retained_characters',0) for x in items);body=sum(len(x['text']) for x in items if x['reason']!='节标题') if all('reason' in x for x in items) else sum(len(x['text']) for x in items if x.get('reason')!='节标题')
        adapted=sum(len(x['text']) for x in items if x['kind'].startswith('source'))
        chapters.append({'chapter':key,'title':title,'file':'chapters/'+key+'.md','status':c['status'],'cjk_characters':cjk,'body_characters':body,'source_adapted_characters':adapted,'literal_source_characters':retained,'literal_retention_ratio':round(retained/body,4) if body else 0,'source_blocks':sum(x['kind'].startswith('source') for x in items),'review':c['review']})
        manifest.append({'chapter':key,'items':items})
    (OUT/'01-manuscript.md').write_bytes(whole.encode('utf-8'))
    state={'schema':'new-principles-expanded.editorial-state@1','updated_at':datetime.now(timezone.utc).isoformat(),'status':'in-progress','baseline_edition':'../2026-10-26-new-principles/01-new-principles.md','requested_work':'全面扩充，作者原话为主，独立成篇，逐章连续修订','complete_chapters':len(chapters),'planned_chapters':len(PLAN),'plan':[{'chapter':k,'title':v,'status':next((c['status'] for c in chapters if c['chapter']==k),'pending')} for k,v in PLAN],'chapters':chapters,'total_cjk_characters':len(re.findall(r'[\u3400-\u9fff]',whole)),'manuscript_sha256':hashlib.sha256(whole.encode()).hexdigest(),'coverage_note':'literal_source_characters is a literal alignment count, not a semantic fidelity or sole-authorship proof; mixed transcript selections were manually bounded.'}
    finished=len(chapters)==len(PLAN) and all(c['status']=='expanded-copyedited' for c in chapters)
    if finished:state['status']='full-expanded-editorial-draft; author-review-pending'
    (OUT/'edition-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'source-manifest.json').write_text(json.dumps({'schema':'new-principles-expanded.paragraph-provenance@1','coordinate_unit':'unicode-code-point','range':'half-open','chapters':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
    (WORK/'used-sources.json').write_text(json.dumps(sources_used,ensure_ascii=False,indent=2),encoding='utf-8')
    intro='# 《新原理》扩充修订稿\n\n'+('前言、22 章及后记已全部展开，并完成本轮逐章通校。旧版约三万字稿与原始资料保留不动。本稿是供作者审阅的完整编辑稿，不写入作者已经采纳的结论。' if finished else '逐章扩充进行中，旧版保留不动；未完成章节不以旧稿或提纲充数。')+'\n\n[阅读全文](01-manuscript.md) · [来源索引](02-source-atlas.md) · [逐段原文与改动](03-paragraph-ledger.md) · [演化与覆盖](04-evolution-and-coverage.md) · [编辑说明](05-editorial-review.md) · [理论关系](06-theory-map.md)\n\n'
    intro+='已完成本轮改写的章节：'+str(len(chapters))+' / '+str(len(PLAN))+'（含前言、后记）。当前正文汉字数：'+str(state['total_cjk_characters'])+'。\n\n'
    intro+='|章节|修订状态|正文汉字|逐字保留的来源字符 / 正文字符|\n|---|---|---:|---:|\n'
    for k,title in PLAN:
        c=next((x for x in chapters if x['chapter']==k),None)
        intro+=f'|{title}|'+(f'[已展开通校](chapters/{k}.md)|{c["cjk_characters"]}|{c["literal_retention_ratio"]:.1%}' if c else '待逐章重写|—|—')+'|\n'
    intro+='\n比例只计算与来源逐字一致的字符，润色后的文字也保留逐段来源和改动记录；它不能代替对思想忠实度与阅读质量的人工判断。原始文章按用户指定底稿使用，原始会话中的 AI 回复另作上下文，不计作作者原话。\n'
    (OUT/'00-readme.md').write_text(intro,encoding='utf-8')
    print(json.dumps({'chapters':len(chapters),'cjk':state['total_cjk_characters'],'recent':chapters[-1] if chapters else None},ensure_ascii=False))

if __name__=='__main__':build()
