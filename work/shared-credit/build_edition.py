def build():
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    oldbytes=(OLD/'02-new-principles.md').read_bytes();oldchapter=(OLD/'01-chapter.md').read_bytes()
    assert sha(oldbytes)==baseline['old_manuscript_sha256'] and sha(oldchapter)==baseline['old_chapter_sha256']
    assert oldbytes.count(oldchapter)==1
    posbytes=oldbytes.index(oldchapter);prefix=oldbytes[:posbytes];suffix=oldbytes[posbytes+len(oldchapter):]
    pos=len(prefix.decode());chapter='## '+c.title+'\n\n';items=[]
    for i,item in enumerate(c.items):
        x=dict(item);x['ordinal']=i;x['chapter_span']=[len(chapter),len(chapter)+len(x['text'])]
        x['document_span']=[pos+a for a in x['chapter_span']]
        chapter+=x['text']+'\n\n';items.append(x)
    newbytes=chapter.encode();whole=prefix+newbytes+suffix
    (OUT/'01-chapter.md').write_bytes(newbytes);(OUT/'02-new-principles.md').write_bytes(whole)
    write_json(OUT/'passage-manifest.json',{'schema':'shared-credit.passages@1','title':c.title,'coordinate':'Unicode code point; half-open','items':items})
    body=[x for x in items if x.get('reason')!='节标题'];new=[x for x in body if not x.get('previous_passage')]
    stats={'chapter_cjk_characters':len(re.findall('[\u3400-\u9fff]',chapter)),
           'combined_cjk_characters':len(re.findall('[\u3400-\u9fff]',whole.decode())),
           'previous_chapter_cjk':len(re.findall('[\u3400-\u9fff]',oldchapter.decode())),
           'body_unicode_characters':sum(len(x['text']) for x in body),
           'source_adapted_characters':sum(len(x['text']) for x in body if x.get('ref')),
           'literal_aligned_source_characters':sum(x.get('retained_characters',0) for x in body),
           'source_blocks':sum(bool(x.get('ref')) for x in body),'editorial_blocks':sum(not x.get('ref') for x in body),
           'source_entries_used':sorted({x['ref'] for x in body if x.get('ref')}),
           'retained_previous_passages':sum(bool(x.get('previous_passage')) for x in items),
           'new_body_characters':sum(len(x['text']) for x in new),
           'new_literal_aligned_source_characters':sum(x.get('retained_characters',0) for x in new),
           'chapter_sha256':sha(newbytes),'combined_sha256':sha(whole),
           'boundary':'Source-adapted does not mean verbatim; first-person editorial writing does not assert author acceptance.'}
    write_json(OUT/'editorial-statistics.json',stats)
    replacement={'schema':'shared-credit.chapter-replacement@1','baseline_file':baseline['old_manuscript'],
                 'baseline_sha256':sha(oldbytes),'previous_chapter_file':baseline['old_chapter_file'],
                 'previous_chapter_sha256':sha(oldchapter),'replace_at_utf8_byte':posbytes,
                 'replace_at_codepoint':pos,'removed_bytes':len(oldchapter),'removed_characters':len(oldchapter.decode()),
                 'inserted_bytes':len(newbytes),'inserted_characters':len(chapter),
                 'chapter_file':'01-chapter.md','combined_file':'02-new-principles.md',
                 'chapter_sha256':sha(newbytes),'combined_sha256':sha(whole),
                 'outside_chapter_byte_preserved':True,'author_acceptance':'requested section-ten extension; not blanket acceptance of editorial changes'}
    write_json(OUT/'replacement-manifest.json',replacement)
    ledger='# 原话、来源改写与编辑补写\n\n此前章节的保留段落带有上一版段落CID和序号，本次新增段落另标来源。区间为Unicode码点半开区间；原始文字不改写。来源改写包括校订，不等于逐字原话。\n\n'
    for x in body:
        ledger+=f'## {x["ordinal"]} · '+('来源选取与改写' if x.get('ref') else '编辑补写')+'\n\n'
        if x.get('previous_passage'):
            p=x['previous_passage'];ledger+=f'上一版单元 {p["ordinal"]}，`{p["cid"]}`；正文文字保留，位置可能调整。\n\n'
        if x.get('ref'):
            r=DATA[x['ref']];a,b=x['source_span'];text=r['text'][a:b]
            ledger+=f'来源：{x["ref"]}，原生时间 {r["time"]}，区间 [{a}, {b})。\n\n'+x['author_assessment']+'。\n\n原话：\n\n'
            ledger+=''.join('> '+line+'\n' for line in text.split('\n'))+'\n成文：\n\n'+x['text']+'\n\n'
            for e in x['edits']:
                before=e['before'].replace('\n','↵').replace('\r','␍').replace('`','ˋ');after=e['after'].replace('\n','↵').replace('\r','␍').replace('`','ˋ')
                ledger+=f'- [{e["source_span"][0]}, {e["source_span"][1]})：`{before}` → `{after}`。\n'
            ledger+='\n'
        else:ledger+=x.get('reason','论述展开')+'。\n\n'+x['text']+'\n\n'
    (OUT/'03-source-ledger.md').write_bytes(ledger.encode())
    oldord=[x['previous_passage']['ordinal'] for x in items if x.get('previous_passage')]
    assert len(oldord)==len(set(oldord))
    omitted=[x['ordinal'] for x in old_manifest['items'] if x['ordinal'] not in oldord]
    write_json(OUT/'reorganization.json',{'retained_previous_ordinals_in_reading_order':oldord,'omitted_previous_ordinals':omitted,'omission_reason':'all prior passage units and headings retained exactly; additions confined to section ten','new_section_count':11})
    assert all(old_manifest['items'][i].get('reason')=='节标题' for i in omitted)
    print(json.dumps(stats,ensure_ascii=False))
