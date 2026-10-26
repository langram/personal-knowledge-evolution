"""Reuse the established immutable-edition workflow for the section-ten addition."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PREV = ROOT / 'work/public-intelligence'

def replace_once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)

prepare = (PREV / 'prepare.py').read_text(encoding='utf-8')
prepare = prepare.replace('2026-10-26-public-intelligence', '2026-10-26-shared-credit')
prepare = prepare.replace("ARCHIVE=C/'public-intelligence-20261026'", "ARCHIVE=C/'shared-credit-20261026'")
prepare = prepare.replace("PRIOR=C/'mathematics-contribution-20261026'", "PRIOR=C/'public-intelligence-20261026'")
prepare = prepare.replace("OLD=BASE/'dossiers/2026-10-26-mathematics-and-contribution'", "OLD=BASE/'dossiers/2026-10-26-public-intelligence'")
prepare = prepare.replace('INTELLIGENCE-REQUEST', 'CREDIT-REQUEST')
prepare = prepare.replace('public-intelligence-reflection-prefix-v1', 'shared-credit-reflection-prefix-v1')
prepare = replace_once(prepare, "block['text'].startswith('我读了你写的增量部分，很有感触') and '融合进文章中去' in block['text']", "block['text'].startswith('关于文章中的第十点，从学生的灵感，到基层的创造') and '不敢提出' in block['text']")
(HERE / 'prepare.py').write_text(prepare, encoding='utf-8', newline='\n')

build = (PREV / 'write_chapter.py').read_text(encoding='utf-8').split('def build():', 1)[1]
build = build.split("if __name__=='__main__':", 1)[0]
build = build.replace('public-intelligence.', 'shared-credit.')
build = build.replace('positive prior reading feedback is recorded; not interpreted as approval of this new draft', 'requested section-ten extension; not blanket acceptance of editorial changes')
build = build.replace('only old section headings replaced by new numbering; all prior body units retained exactly', 'all prior passage units and headings retained exactly; additions confined to section ten')
(HERE / 'build_edition.py').write_text('def build():\n' + build.lstrip('\n'), encoding='utf-8', newline='\n')

verify = (PREV / 'verify_text.py').read_text(encoding='utf-8').split('def sidecars(', 1)[0]
verify = verify.replace('INTELLIGENCE-REQUEST', 'CREDIT-REQUEST').replace("'pi/text-verification@1'", "'sc/text-verification@1'")
verify += "\nif __name__=='__main__':\n    selected,stats,result=verify();print(json.dumps(result,ensure_ascii=False))\n"
(HERE / 'verify_text.py').write_text(verify, encoding='utf-8', newline='\n')

stage = (PREV / 'stage_archive.py').read_text(encoding='utf-8')
stage = stage.replace('20261026-public-intelligence-v1', '20261026-shared-credit-v1')
stage = stage.replace("COL='public-intelligence-20261026'", "COL='shared-credit-20261026'")
stage = stage.replace("{'pi':'urn:pkst:editorial:public-intelligence:1'}", "{'sc':'urn:pkst:editorial:shared-credit:1'}")
stage = stage.replace("'pi/", "'sc/").replace("'pi:source_span'", "'sc:source_span'")
stage = stage.replace('INTELLIGENCE-REQUEST', 'CREDIT-REQUEST')
stage = stage.replace("C/'mathematics-contribution-20261026/report.json'", "C/'public-intelligence-20261026/report.json'")
stage = stage.replace('2026-10-26 knowledge and public intelligence integration', '2026-10-26 shared credit and timely sharing extension')
stage = stage.replace('Knowledge-intelligence loop and common infrastructure explain the institutional context of the prior mathematics case; no retraction or empirical validation.', 'Attribution evidence, timely sharing and separation of proposals from execution extend the prior case; no guaranteed safety or causal validation asserted.')
stage = stage.replace('Requested knowledge/intelligence reflection integrated into existing chapter; previous body passages retained and other chapters byte-preserved.', 'Requested shared-credit reflection integrated into section ten; all previous passages retained and other sections byte-preserved.')
stage = stage.replace('knowledge/intelligence reflection integrated with mathematics case; exact replacement and prior passage preservation', 'section-ten shared-credit reflection; exact replacement and all prior passage preservation')
stage = stage.replace('requested public-intelligence theory integration', 'requested section-ten shared-credit integration')
stage = stage.replace('append public-intelligence revision', 'append shared-credit revision')
(HERE / 'stage_archive.py').write_text(stage, encoding='utf-8', newline='\n')
print('Prepared source capture, text replay, build helper, and archive staging scripts.')
