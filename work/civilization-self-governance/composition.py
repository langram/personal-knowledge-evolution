"""Source-led additions with reversible text and byte-level insertion records."""
import difflib
import json
import re
from prepare import ARCHIVE, OLD, OUT, sha, write_json

EVENTS={e['ref']:e for e in json.loads((ARCHIVE/'capture.json').read_bytes())['events']}

class Section:
    def __init__(self,title,filename,marker,level=2):
        self.title=title; self.filename=filename; self.marker=marker; self.level=level; self.items=[]
    def add(self,text,reason='补足论证',basis=()):
        self.items.append({'kind':'editorial-addition','text':text.strip(),'reason':reason,'basis_refs':list(basis),
                           'author_acceptance':'editorial proposal; no individual author adoption asserted'})
    def h(self,text): self.add('#'*(self.level+1)+' '+text,'节标题')
    def src(self,paragraph,start=None,end=None,new=None,reason='保留原话，整理语序并限定成立条件'):
        ref='CIVILIZATION-REPLY'; e=EVENTS[ref]; text=e['text']
        match=list(re.finditer(r'[^\n]+(?:\n(?!\n)[^\n]+)*',text))[paragraph]
        a,b=match.span()
        if start is not None:a=text.index(start,a,b)
        if end is not None:b=text.index(end,a,b)+len(end)
        original=text[a:b]; result=original if new is None else new.strip()
        ops=difflib.SequenceMatcher(None,original,result,autojunk=False).get_opcodes()
        self.items.append({'kind':'source-exact' if original==result else 'source-adaptation','text':result,
            'ref':ref,'source_role':e['role'],'source_span':[a,b],'source_sha256':sha(original.encode()),
            'retained_characters':sum(j-i for tag,i,j,k,l in ops if tag=='equal'),'reason':reason,
            'edits':[{'operation':tag,'source_span':[a+i,a+j],'output_span':[k,l],
                      'before':original[i:j],'after':result[k:l]} for tag,i,j,k,l in ops if tag!='equal'],
            'author_acceptance':'original preserved; editorial adaptation available for author review'})
    def render(self,offset):
        result='#'*self.level+' '+self.title+'\n\n'
        for i,item in enumerate(self.items):
            item.update({'ordinal':i,'section_span':[len(result),len(result)+len(item['text'])],
                         'document_span':[offset+len(result),offset+len(result)+len(item['text'])]})
            result+=item['text']+'\n\n'
        return result

def assemble(sections):
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    old=OLD.read_bytes(); assert sha(old)==baseline['sha256']
    positions=[]
    for s in sections:
        marker=s.marker.encode(); assert old.count(marker)==1,s.marker
        positions.append((old.index(marker),s))
    positions.sort(key=lambda x:x[0]); whole=b''; cursor=0; records=[]; ordered=[]
    for at,s in positions:
        whole+=old[cursor:at]
        new_at=len(whole)
        block=s.render(len(whole.decode())).encode()
        (OUT/s.filename).write_bytes(block)
        records.append({'file':s.filename,'title':s.title,'level':s.level,'marker':s.marker,
                        'old_byte_offset':at,'new_byte_offset':new_at,'bytes':len(block),'sha256':sha(block)})
        whole+=block; cursor=at; ordered.append(s)
    whole+=old[cursor:]
    (OUT/'02-new-principles.md').write_bytes(whole)
    bundle='# 本次增补正文\n\n'+''.join((OUT/s.filename).read_text(encoding='utf-8') for s in ordered)
    (OUT/'08-edition-additions.md').write_bytes(bundle.encode())
    write_json(OUT/'passage-manifest.json',{'schema':'csg/passages@1','coordinate':'Unicode code points, half-open',
        'sections':[{'title':s.title,'file':s.filename,'level':s.level,'items':s.items} for s in ordered]})
    write_json(OUT/'insertion-manifest.json',{'schema':'csg/insertions@1','baseline_file':baseline['manuscript'],
        'baseline_sha256':sha(old),'combined_sha256':sha(whole),'original_bytes':len(old),
        'insertions':records,'outside_insertions_byte_preserved':True,'prior_final_appendix_preserved':True})
    units=[x for s in ordered for x in s.items]; selected=[x for x in units if 'ref' in x]
    cjk=lambda data:len(re.findall('[\u3400-\u9fff]',data.decode()))
    metrics={'sections':[{'file':s.filename,'title':s.title,'cjk':cjk((OUT/s.filename).read_bytes())} for s in ordered],
        'added_cjk':sum(cjk((OUT/s.filename).read_bytes()) for s in ordered),'combined_cjk':cjk(whole),
        'combined_sha256':sha(whole),'source_events':len(EVENTS),'source_spans':len(selected),'passage_units':len(units),
        'author_source_characters_selected':sum(x['source_span'][1]-x['source_span'][0] for x in selected),
        'author_literal_retained_characters':sum(x['retained_characters'] for x in selected),
        'boundary':'Literal overlap measures selected source retention, not proportion of the entire book or author acceptance.'}
    write_json(OUT/'editorial-statistics.json',metrics)
    ledger='# 原话与本次编辑对照\n\n完整原话见00-civilization-reply.txt；研究委托及AI答复分别保存。下列每个改写单元可追溯到原话的字符区间，补写单独标记。新增第一人称表述是供作者审阅的编辑稿，不自动视为作者已经逐项接受。\n\n'
    for s in ordered:
        ledger+='## '+s.title+'\n\n'
        for x in s.items:
            if x['reason']=='节标题':continue
            ledger+='### 单元 '+str(x['ordinal'])+'\n\n'
            if 'ref' in x:
                e=EVENTS[x['ref']];a,b=x['source_span']
                ledger+=f"来源：{x['ref']}；角色：{e['role']}；原生时间：{e['time']}；Unicode区间：[{a}, {b})。\n\n原话：\n\n"
                ledger+='\n'.join('> '+line for line in e['text'][a:b].splitlines())+'\n\n成文：\n\n'+x['text']+'\n\n编辑理由：'+x['reason']+'。\n\n'
            else:ledger+='编辑补写：'+x['reason']+'。\n\n'+x['text']+'\n\n'
    (OUT/'03-source-ledger.md').write_bytes(ledger.encode())
    print(json.dumps(metrics,ensure_ascii=False,indent=2))
