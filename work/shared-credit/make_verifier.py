"""Reuse saved-object replay and keep activation specific to this revision."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
prior=(HERE.parent/'public-intelligence/verify_archive.py').read_text(encoding='utf-8')
head=prior.split("    readme = BASE / 'README.md'",1)[0]
head=head.replace("C / 'mathematics-contribution-20261026/report.json'", "C / 'public-intelligence-20261026/report.json'")
head=head.replace('INTELLIGENCE-REQUEST','CREDIT-REQUEST')
head=head.replace('我读了你写的增量部分，很有感触','关于文章中的第十点，从学生的灵感，到基层的创造')
tail=r'''
    assert omitted == [] and retained == list(range(len(prior['passages'])))
    oldtext = oldchapter.decode()
    a, b = oldtext.index('### 十、'), oldtext.index('### 十一、')
    u, v = body.index('### 十、'), body.index('### 十一、')
    assert oldtext[:a] == body[:u] and oldtext[b:] == body[v:]
    assert body[u:v].encode() == (OUT / '05-section-ten.md').read_bytes()
    metrics = json.loads((ARCHIVE / 'section-metrics.json').read_bytes())
    readme = BASE / 'README.md'
    text = readme.read_bytes().decode()
    assert text.count('**212,356 个当前来源记录**') == 1
    text = text.replace('**212,356 个当前来源记录**', '**212,357 个当前来源记录**', 1)
    anchor = '2026 年 10 月 26 日知识与公共智能融合稿：'
    assert text.count(anchor) == 1
    latest = f'2026 年 10 月 26 日第十节扩展稿：**[《从学生的灵感，到基层的创造》，{metrics["section_ten_cjk"]:,} 汉字](dossiers/2026-10-26-shared-credit/05-section-ten.md)**；[完整案例章节](dossiers/2026-10-26-shared-credit/01-chapter.md)；[《新原理》全文，{stats["combined_cjk_characters"]:,} 汉字](dossiers/2026-10-26-shared-credit/02-new-principles.md)。补充贡献记录的技术条件、荣誉分配史、及时分享的反馈与提出和执行的区别。原话和全部旧段落保留。[归档收据](dossiers/2026-10-26-shared-credit/09-archive-receipt.md)。\n\n'
    text = text.replace(anchor, latest.replace('\\n','\n') + anchor, 1)
    a = text.index('当前统一入口为')
    b = text.index('[ChatGPT 导入时的目录报告]', a)
    paragraph = f'当前统一入口为 [2026-10-26 共同贡献增量目录](contributions/codex/catalog/{pointer["report"]})，[启用状态](contributions/codex/shared-credit-20261026/status.json)记录核验后切换。现有 {count:,} 条来源事件；相比[公共智能目录](contributions/codex/catalog/{baseline["pointer"]["report"]})仅增加本次对第十节的作者补充。12条此前来源复用原身份；编辑正文、历史核对及关系分别保存。\n\n'
    text = text[:a] + paragraph.replace('\\n','\n') + text[b:]
    result = {
        'schema':'sc/archive-verification@1', 'status':'pass',
        'recorded_at':datetime.now(timezone.utc).isoformat(),
        'snapshot':report['snapshot'], 'federated_snapshot':pointer['snapshot'],
        'chapter_sha256':stats['chapter_sha256'], 'combined_sha256':stats['combined_sha256'],
        'source_entries_checked':len(selected), 'source_units_replayed':quote_count,
        'all_passage_units':len(report['passages']), 'all_prior_passages_preserved':len(retained),
        'outside_section_ten_byte_preserved':True, 'standalone_section_replayed':True,
        'frozen_files_checked':len(report['files']), 'archive_blocks_checked':len(checked),
        'current_native_events':count, 'chapter_replacement_and_inverse_passed':True,
        'request_retrieval_passed':True,
        'full_reference_graph_nodes_checked_at_staging':report['full_reference_graph_nodes'],
        'review_scope':'Codex replay of saved objects; no Claude review, publication, or blanket author acceptance',
    }
    write_json(ARCHIVE / 'verification.json', result)
    assert json.loads(current.read_bytes()) == baseline['pointer'], 'Another writer changed catalog'
    temp = C / 'catalog/current.sc.tmp'
    assert not temp.exists()
    write_json(temp, pointer)
    temp.replace(current)
    write_json(ARCHIVE / 'status.json', {
        'status':'activated-after-verification','recorded_at':datetime.now(timezone.utc).isoformat(),
        'pointer':pointer,'verification':'verification.json','text_verification':'text-verification.json',
        'author_adoption':False,'public_release':False,
    })
    receipt = f"""# 第十节共同贡献扩展稿归档收据

第十节 {metrics['section_ten_cjk']:,} 汉字，案例章节 {stats['chapter_cjk_characters']:,} 汉字，《新原理》全文 {stats['combined_cjk_characters']:,} 汉字。

新增本次作者发言1条，复用12个来源；原文、原生时间与取证坐标保持。当前目录共 {count:,} 条来源事件。

42个来源选取单元和90个编辑单元通过重放；前版79个段落单元全部保留，新增只在第十节，其他小节与全书其他章节按原字节保留。单独阅读版与全文中的第十节一致，整章替换和逆向恢复均通过。

历史依据、作者原话、编辑修订分别保存。佩雷尔曼的两次拒奖区分；分享加速与降低错误执行概率保留为有条件的机制设想，不记作实证成功或作者采纳所有改写。

专题闭包 {report['closure_blocks']} 个对象，{len(report['files'])} 份正文及附录文件；暂存时对完整引用图 {report['full_reference_graph_nodes']:,} 个节点检查闭合与无环。另从保存对象重放文件、来源、时间、检索与数据库完整性。旧来源解析沿用此前收据；没有宣称重新提炼全部语料。

专题根：`{report['snapshot']}`。

统一根：`{pointer['snapshot']}`。

父统一根：`{baseline['pointer']['snapshot']}`。

章节 SHA-256：`{stats['chapter_sha256']}`。

全文 SHA-256：`{stats['combined_sha256']}`。

[文字核验](../../contributions/codex/shared-credit-20261026/text-verification.json) · [归档核验](../../contributions/codex/shared-credit-20261026/verification.json) · [对象清单](../../contributions/codex/shared-credit-20261026/report.json) · [启用状态](../../contributions/codex/shared-credit-20261026/status.json)

仅本地保存。旧稿与旧目录保留，本轮没有新的Claude审阅。本收据在根生成后写入，不参与自身根的哈希。
"""
    (OUT / '09-archive-receipt.md').write_bytes(receipt.encode())
    readme.write_bytes(text.encode())
    missing = []
    for path in OUT.glob('*.md'):
        for target in re.findall(r'\]\(([^\s)]+)\)', path.read_bytes().decode()):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                continue
            local = unquote(target.split('#', 1)[0])
            if local and not (path.parent / local).exists():
                missing.append((path.name, target))
    assert not missing, missing
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    verify_activate()
'''
# The generated Python must use actual newline escapes in these two literals.
tail=tail.replace("\\\\n", "\\n")
(HERE/'verify_archive.py').write_text(head+tail,encoding='utf-8',newline='\n')
print('Generated saved-object verifier with section-ten and activation checks.')
