"""Reversible bilingual coherence edits and a fully attributed new author passage."""
import difflib
import json
import re
from pathlib import Path
from prepare import ARCHIVE, BASE, EDITION, OLD, OLD_EN, OUT, PUBLIC, WORK, sha, write_json
from edits import EDITS
SOURCES={e['id']:['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW'] for e in EDITS}
FRAGMENTS=['01-institutional-gap','02-empirical-reflection']

def read(path):
    return path.read_bytes().decode('utf-8')

def sections(text):
    points = list(re.finditer(r'^## (.+)$', text, re.M))
    return [{'title':m[1], 'span':[m.start(),points[i+1].start() if i+1<len(points) else len(text)]}
            for i,m in enumerate(points)]

def urls(text):
    return re.findall(r'\]\((https?://[^)\s]+)\)',text)

def headings(text):
    return re.findall(r'^(#{2,6}) (.+)$',text,re.M)

def assemble(language, baseline):
    chapter_map=sections(baseline);edits=[]
    for spec in EDITS:
        chapter=chapter_map[spec['chapter']-1];start,end=chapter['span']
        content=baseline[start:end];anchor=spec['anchors'][language];mode=spec['mode']
        if mode=='insert-heading':
            assert content.count(anchor+'\n')==1,(language,spec['id'],anchor)
            pos=start+content.index(anchor+'\n');before='';after=spec['text'][language]+'\n\n'
        elif mode=='substring':
            assert content.count(anchor)==1,(language,spec['id'],anchor)
            pos=start+content.index(anchor);before=anchor;after=spec['text'][language]
        else:
            matches=[p for p in content.split('\n\n') if p.startswith(anchor)]
            assert len(matches)==1,(language,spec['id'],anchor)
            before=matches[0];assert content.count(before)==1
            pos=start+content.index(before)
            after=before+'\n\n'+spec['text'][language] if mode=='append' else spec['text'][language]
        edits.append({'id':spec['id'],'chapter':spec['chapter'],'language':language,
            'old_span':[pos,pos+len(before)],'before':before,'after':after,
            'kind':'insert' if not before else 'replace','rationale':spec['rationale'],
            'source_refs':SOURCES[spec['id']],
            'attribution':'Author-requested editorial integration; baseline wording retains prior provenance; additions are not automatically author-approved.'})
    edits.sort(key=lambda e:e['old_span']);pieces=[];cursor=0;newpos=0
    for e in edits:
        start,end=e['old_span'];assert start>=cursor
        gap=baseline[cursor:start];pieces += [gap,e['after']];newpos+=len(gap)
        e['new_span']=[newpos,newpos+len(e['after'])];newpos+=len(e['after']);cursor=end
        e['before_sha256']=sha(e['before'].encode());e['after_sha256']=sha(e['after'].encode())
    pieces.append(baseline[cursor:]);return ''.join(pieces),edits

def build():
    assert not (ARCHIVE/'report.json').exists(),'Do not rebuild a frozen edition.'
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    originals={'zh':read(OLD),'en':read(OLD_EN)}
    assert sha(originals['zh'].encode())==baseline['sha256']
    assert sha(originals['en'].encode())==baseline['english_sha256']
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events'];byref={e['ref']:e for e in events}
    results={};changes=[]
    for lang,original in originals.items():
        text,edits=assemble(lang,original);results[lang]=text;changes+=edits
        name='01-new-principles.zh.md' if lang=='zh' else '02-new-principles.en.md'
        (OUT/name).write_bytes(text.encode())
        patch=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),
            fromfile='edition-14/'+name,tofile=EDITION+'/'+name))
        (OUT/f'03-{lang}-revisions.patch').write_bytes(patch.encode())
        additions='\n\n'.join(read(WORK/'fragments'/f'{stem}.{lang}.md').rstrip() for stem in FRAGMENTS)+'\n'
        (OUT/f'06-additions.{lang}.md').write_bytes(additions.encode())
    manifest={'schema':'ic/revision-manifest@1','coordinate':'unicode-scalar-half-open',
        'edition':EDITION,'baseline_edition':'14-civilization-attention',
        'baseline_sha256':{l:sha(t.encode()) for l,t in originals.items()},
        'result_sha256':{l:sha(t.encode()) for l,t in results.items()},'changes':changes,
        'unchanged_boundary':'All text outside the recorded spans is preserved exactly; source utterances are never overwritten.'}
    write_json(OUT/'revision-manifest.json',manifest)
    write_json(OUT/'zh-revision-manifest.json',{**manifest,'changes':[e for e in changes if e['language']=='zh']})
    zsections=sections(results['zh']);esections=sections(results['en'])
    assert len(zsections)==len(esections)==32
    old_by_title={l:{r['title']:t[slice(*r['span'])] for r in sections(t)} for l,t in originals.items()}
    ledger=[]
    for i,(z,e) in enumerate(zip(zsections,esections),1):
        ztext=results['zh'][slice(*z['span'])];etext=results['en'][slice(*e['span'])]
        zheads=headings(ztext);eheads=headings(etext)
        assert [h[0] for h in zheads]==[h[0] for h in eheads],(z['title'],e['title'])
        assert urls(ztext)==urls(etext),(z['title'],'citation mismatch')
        sourcefile=f'zh-chapters/{i:02}.md';engfile=f'en-chapters/{i:02}.md'
        for name,txt in [(sourcefile,ztext),(engfile,etext)]:
            p=WORK/name;p.parent.mkdir(exist_ok=True);p.write_bytes(txt.encode())
        unchanged=old_by_title['zh'].get(z['title'])==ztext and old_by_title['en'].get(e['title'])==etext
        ledger.append({'id':f'{i:02}','title_zh':z['title'],'title_en':e['title'],
            'char_span':z['span'],'english_char_span':e['span'],'source_file':sourcefile,'english_source_file':engfile,
            'sha256':sha(ztext.encode()),'english_sha256':sha(etext.encode()),'english_source_sha256':sha(etext.encode()),
            'section_map':[{'level':len(a[0]),'zh':a[1],'en':b[1]} for a,b in zip(zheads,eheads)],
            'external_links':urls(ztext),'review':{'status':'inherited-byte-identical' if unchanged else 'editorial-reviewed',
                'scope':'Changed English passages and adjacent context compared with Chinese; full chapter structure and citations checked. Unchanged wording inherited, not claimed freshly reread in full; not author approval or proof of theory'}})
    write_json(OUT/'translation-ledger.json',{'schema':'ic/translation-ledger@1','coordinate':'unicode-scalar-half-open',
        'edition':EDITION,'chapters':ledger,'method':'Idiomatic English adaptation; unchanged translations inherited byte-for-byte from edition 14.'})
    # Record exact recoverable author wording, separate from semantic attribution.
    passages=[]
    for edit in (e for e in changes if e['language']=='zh'):
        for i,m in enumerate(re.finditer(r'(?s)(\S.*?)(?=\n\n|\Z)',edit['after']),1):
            paragraph=m[1];exact=[]
            for ref in edit['source_refs']:
                event=byref[ref]
                if event['role']!='user':continue
                for block in difflib.SequenceMatcher(None,event['text'],paragraph,autojunk=False).get_matching_blocks():
                    if block.size<24:continue
                    exact.append({'ref':ref,'source_span':[block.a,block.a+block.size],
                        'paragraph_span':[block.b,block.b+block.size],
                        'text':paragraph[block.b:block.b+block.size]})
            passages.append({'id':f"{edit['id']}-{i:03}",'edit':edit['id'],
                'document_span':[edit['new_span'][0]+m.start(1),edit['new_span'][0]+m.end(1)],
                'sha256':sha(paragraph.encode()),'source_refs':edit['source_refs'],'exact_author_spans':exact,
                'attribution':'Mixed author-led adaptation and editorial explanation; source association does not attribute every sentence to the author.',
                'author_wording_approved':False})
    write_json(OUT/'passage-manifest.json',{'schema':'ic/passage-manifest@1','coordinate':'unicode-scalar-half-open',
        'minimum_exact_span_characters':24,'passages':passages})
    timeline=[{'step':i,'ref':e['ref'],'role':e['role'],'event_time':e['native_event_time'],
        'occurrence':e['occurrence'],'content':e['content'],'text_sha256':e['text_sha256'],
        'status':'prior release context' if i==1 else 'author proposal' if e['role']=='user' else 'assistant response, not automatic author endorsement'}
        for i,e in enumerate(events,1)]
    write_json(OUT/'07-thought-evolution.json',{'schema':'ic/evolution@1','previous_edition':'14-civilization-attention',
        'stages':timeline,'boundary':'Native message timestamps describe visible speech events, not first invention; no hidden reasoning captured.'})
    from write_support import support
    support(results,originals,changes,ledger,passages,events,timeline)

if __name__=='__main__':build()
