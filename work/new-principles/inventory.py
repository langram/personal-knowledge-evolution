import json,sqlite3,re,sys
from collections import Counter,defaultdict
from pathlib import Path
BASE=Path(__file__).resolve().parents[2]/'outputs/personal-thought-archive'
OUT=Path(__file__).resolve().parent
THEMES={
 '01-math-science':['新原理','数学与科学','数学的数学','第一性原理','奥卡姆'],
 '02-limits-self-reference':['芝诺','悖论','自指','同伦','不完备','对角线'],
 '03-category-duality':['范畴论','对偶子','对偶体','米田','富集','万有性质'],
 '04-fixedpoint-emergence':['不动点','最小化','最大化','涌现','对称性','REEC'],
 '05-physics-life':['熵增','耗散结构','物理世界','生命','DNA','时间箭头'],
 '06-consciousness-transfer':['意识','脑机','知识迁移','认知','感知','永生'],
 '07-language-knowledge':['语言','语义','知识系统','知识体系','知识图谱','文明DNA'],
 '08-game-cooperation':['以牙还牙','博弈','纳什','合作','MAOA','契约'],
 '09-institutions-power':['权力','不平等','垄断','分配','新体制','金字塔'],
 '10-network-agi':['社会神经网络','智能网络','传感器','机器人','AGI','碳基'],
 '11-dynamic-decision':['动态权重','权重决策','集体决策','垃圾邮件','预测准确'],
 '12-needs-resources':['个人需求','个体需求','集体资源','公共资源','正态分布','按需'],
 '13-merkle-knowledge':['Merkle-DAG','merkle-DAG','Merkle DAG','merkle架构','公共知识','CID'],
 '14-new-language':['newlanguage','新语言','编程语言','语义归一','语义契约'],
 '15-hotpath-launcher':['hotpath','HotPath','quick launcher','quick-launcher','冷路径','热路径'],
 '16-fpm-structoken':['Structoken','structoken','FPM','fpm','模型压缩','token','不动点最小化'],
 '17-merkle-vm':['MerkleVM','merkleVM','虚拟机','运行时','RocksDB'],
 '18-rea-portability':['REA','rea','逆向','信息孤岛','兼容','数据主权'],
 '19-development-construction':['工具链','编译器','构造','验证器','非确定','确定性'],
 '20-cloud-seed':['云存储','云计算','云算力','租','买断','从我一个人'],
 '21-production-contribution':['贡献','生产','生产力','组织','分配方式','开源'],
 '22-science-education':['科学研究','教育','学习','科学家','创新','共享'],
 '23-fiction-game':['自我实现','科幻','小说','游戏','世界观','影视'],
 '24-freezone-evolution':['自由区','非暴力','和平','逐步替代','自愿','退出'],
 '25-multidevice-agents':['多智能体','多个AI','交叉','多方','macbook','windows'],
 '26-identity-effects':['授权','撤销','权限','身份','真值','真实世界'],
 '27-evidence-cost':['反例','负结果','实验','能耗','成本','比较','基线']}
p=json.loads((BASE/'contributions/codex/catalog/current.json').read_text());db=sqlite3.connect((BASE/p['database']).as_uri()+'?mode=ro',uri=True)
query='''SELECT o.cid,o.role,o.event_time,o.event_format,s.platform,s.native_thread_id,c.cid,c.text
 FROM current_occurrences o JOIN sources s ON s.cid=o.source JOIN parts p ON p.occurrence=o.cid JOIN content c ON c.cid=p.content
 WHERE o.role IN ('user','human','Prompted')'''
rows=[];seen=set();stats=Counter();by=defaultdict(list)
for oc,role,t,fmt,platform,thread,content,text in db.execute(query):
 token=(oc,content)
 if token in seen:continue
 seen.add(token);stats['source_parts']+=1
 # Never discard original source. Only mark context/config wrappers as outside this authored-idea retrieval.
 wrapper=text.startswith(('<environment_context>','<instructions>','<system','# AGENTS.md','<permissions','You are Codex','## Global Codex Memory','<user_instructions>'))
 if wrapper:stats['context_wrappers_not_ranked']+=1;continue
 topics={k:[w for w in words if w in text] for k,words in THEMES.items()};topics={k:v for k,v in topics.items() if v}
 if not topics:stats['no_keyword_hit']+=1;continue
 record={'occurrence':oc,'role':role,'time':t,'time_format':fmt,'platform':platform,'thread':thread,'content':content,'text':text,'themes':topics,'characters':len(text)}
 i=len(rows);rows.append(record)
 for topic in topics:by[topic].append(i)
stats['retrieved_parts']=len(rows)
(OUT/'retrieval.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
inventory={}
for topic,indexes in by.items():
 unique={rows[i]['content']:i for i in indexes};items=list(unique.values())
 def rank(i):
  r=rows[i];n=r['characters'];return (len(r['themes'][topic])*5+min(n,2000)/400)-(10 if n>20000 else 0)-(6 if any(s in r['text'][:150] for s in ['以下是claude','以下是Claude','评估结果','运行以下','Task','tool_call','Codex：']) else 0)
 selected=[]
 for platform in ['chatgpt','claude-ai','gemini','codex-local','claude-code']:
  selected.extend(sorted([i for i in items if rows[i]['platform']==platform and 100<=rows[i]['characters']<=20000],key=rank,reverse=True)[:6])
 selected=list(dict.fromkeys(selected));inventory[topic]={'terms':THEMES[topic],'parts':len(indexes),'unique_content':len(unique),'platforms':dict(Counter(rows[i]['platform'] for i in indexes)),
  'candidates':[{'row':i,**{k:rows[i][k] for k in ['occurrence','platform','time','characters']},'head':rows[i]['text'][:140].replace('\n',' ')} for i in selected]}
(OUT/'inventory.json').write_text(json.dumps({'baseline':p,'counts':dict(stats),'themes':inventory},ensure_ascii=False,indent=2),encoding='utf-8')
for key,value in inventory.items():print(key,value['parts'],value['unique_content'],json.dumps(value['platforms'],ensure_ascii=False))
print('counts',dict(stats))
