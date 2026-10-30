"""Source spans and reversible edits for two insertions into an immutable edition."""
import difflib
import json
import re
from prepare import ARCHIVE, OLD, OUT, sha, write_json

EVENTS = {e['ref']:e for e in json.loads((ARCHIVE/'capture.json').read_bytes())['events']}

class Section:
    def __init__(self, title, filename):
        self.title=title; self.filename=filename; self.items=[]
    def add(self,text,reason='编辑补充论证',basis=()):
        self.items.append({'kind':'editorial-addition','text':text.strip(),'reason':reason,'basis_refs':list(basis),
                           'author_acceptance':'editorial proposal; no individual author adoption asserted'})
    def h(self,text): self.add('### '+text,'节标题')
    def src(self,ref,paragraph,start=None,end=None,new=None,replacements=(),reason='保留原话并整理语序与条件'):
        e=EVENTS[ref]; text=e['text']
        match=list(re.finditer(r'[^\n]+(?:\n(?!\n)[^\n]+)*',text))[paragraph]
        a,b=match.span()
        if start is not None: a=text.index(start,a,b)
        if end is not None: b=text.index(end,a,b)+len(end)
        original=text[a:b]; result=original if new is None else new.strip()
        for before,after in replacements:
            assert result.count(before)==1,(ref,paragraph,before)
            result=result.replace(before,after)
        ops=difflib.SequenceMatcher(None,original,result,autojunk=False).get_opcodes()
        self.items.append({'kind':'source-exact' if result==original else 'source-adaptation','text':result,
            'ref':ref,'source_role':e['role'],'source_span':[a,b],'source_sha256':sha(original.encode()),
            'retained_characters':sum(j-i for tag,i,j,k,l in ops if tag=='equal'),'reason':reason,
            'edits':[{'operation':tag,'source_span':[a+i,a+j],'output_span':[k,l],
                      'before':original[i:j],'after':result[k:l]} for tag,i,j,k,l in ops if tag!='equal'],
            'author_acceptance':'source text is preserved; adaptation remains an editorial proposal'})
    def render(self,offset):
        result='## '+self.title+'\n\n'
        for i,item in enumerate(self.items):
            item.update({'ordinal':i,'section_span':[len(result),len(result)+len(item['text'])],
                         'document_span':[offset+len(result),offset+len(result)+len(item['text'])]})
            result+=item['text']+'\n\n'
        return result

def assemble(chapter,appendix):
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    old=OLD.read_bytes(); assert sha(old)==baseline['sha256']
    marker='## 从一个人的云存储开始\n'.encode()
    assert old.count(marker)==1
    at=old.index(marker)
    body=chapter.render(len(old[:at].decode())).encode()
    interim=old[:at]+body+old[at:]
    separator=b'' if interim.endswith(b'\n\n') else b'\n' if interim.endswith(b'\n') else b'\n\n'
    tail=appendix.render(len((interim+separator).decode())).encode()
    whole=interim+separator+tail
    for section,data in [(chapter,body),(appendix,tail)]: (OUT/section.filename).write_bytes(data)
    (OUT/'02-new-principles.md').write_bytes(whole)
    manifest={'schema':'rr/passages@1','coordinate':'Unicode code points, half-open',
        'sections':[{'title':s.title,'file':s.filename,'items':s.items} for s in [chapter,appendix]]}
    write_json(OUT/'passage-manifest.json',manifest)
    write_json(OUT/'insertion-manifest.json',{'schema':'rr/insertions@1','baseline_file':baseline['manuscript'],
        'baseline_sha256':sha(old),'combined_sha256':sha(whole),'original_bytes':len(old),
        'body':{'file':chapter.filename,'old_byte_offset':at,'new_byte_offset':at,'bytes':len(body),'sha256':sha(body)},
        'appendix':{'file':appendix.filename,'old_byte_offset':len(old),'new_byte_offset':len(interim+separator),
            'separator_utf8':separator.decode(),'bytes':len(tail),'sha256':sha(tail)},
        'outside_insertions_byte_preserved':True,'appendix_is_final':True})
    cjk=lambda data: len(re.findall('[\u3400-\u9fff]',data.decode()))
    units=chapter.items+appendix.items
    selected=[x for x in units if x.get('source_role')=='user']
    stats={'chapter_cjk':cjk(body),'appendix_cjk':cjk(tail),'combined_cjk':cjk(whole),
        'chapter_sha256':sha(body),'appendix_sha256':sha(tail),'combined_sha256':sha(whole),
        'source_spans':sum('ref' in x for x in units),'passage_units':len(units),
        'author_source_characters_selected':sum(x['source_span'][1]-x['source_span'][0] for x in selected),
        'author_literal_retained_characters':sum(x['retained_characters'] for x in selected),
        'source_events':len(EVENTS),'boundary':'Character matches are not a claim that editor additions were authored or accepted by the user.'}
    write_json(OUT/'editorial-statistics.json',stats)
    ledger='# 原话与本次编辑对照\n\n七条原始发言分别保存为 00- 开头的文本，完整索引见 [来源索引](00-sources.json)。原生时间只表示这次发言发生的时间，不冒充思想首次产生的时间。作者、AI答复和本次补写分开记录；第一人称的编辑补写供作者审阅，不自动算作作者已经接受。\n\n'
    for section in [chapter,appendix]:
        ledger+='## '+section.title+'\n\n'
        for x in section.items:
            if x['reason']=='节标题': continue
            ledger+='### 单元 '+str(x['ordinal'])+'\n\n'
            if 'ref' in x:
                e=EVENTS[x['ref']]; a,b=x['source_span']
                ledger+=f"来源：{x['ref']}；角色：{e['role']}；时间：{e['time']}；Unicode 区间：[{a}, {b})。\n\n原话：\n\n"
                ledger+='\n'.join('> '+line for line in e['text'][a:b].splitlines())+'\n\n成文：\n\n'+x['text']+'\n\n'
                ledger+='编辑理由：'+x['reason']+'。逐字符变化见 passage-manifest.json。\n\n'
            else:
                ledger+='编辑补写：'+x['reason']+'。\n\n'+x['text']+'\n\n'
    (OUT/'03-source-ledger.md').write_bytes(ledger.encode())
    print(json.dumps(stats,ensure_ascii=False))
