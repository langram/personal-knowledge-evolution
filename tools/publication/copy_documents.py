"""Copy preserved manuscript history and tooling into the public release."""
import collections,hashlib,json,os
from pathlib import Path
from safety import sanitize,tree
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'outputs/personal-thought-archive';HERE=Path(__file__).resolve().parent
DEST=ROOT/'publication/personal-knowledge-evolution'
EXT={'.md','.json','.py','.txt','.tsv','.log'}
SKIP={'raw','objects','.private','__pycache__','staging','.git'}
def sha(b):return hashlib.sha256(b).hexdigest()

def main():
    manifest=[];omitted=[];findings=[]
    for root,prefix in [(BASE,Path('archive')),(ROOT/'work',Path('work'))]:
        for folder,dirs,names in os.walk(root):
            dirs[:]=[d for d in dirs if d not in SKIP and not (root.name=='work' and d=='publishing')]
            for name in names:
                path=Path(folder)/name;rel=path.relative_to(root)
                if path.suffix not in EXT:continue
                # Search caches and temporary native transcripts are not editorial documents.
                if root.name=='work' and path.suffix!='.py':
                    if rel.parts[0] not in {'new-principles','new-principles-expanded','mathematics-contribution','public-intelligence','shared-credit'}:
                        omitted.append({'path':str(prefix/rel),'reason':'working search or native transcript cache'});continue
                    if path.name in {'retrieval.jsonl','inventory.json'} or 'web' in rel.parts or path.name.endswith('captures.json'):
                        omitted.append({'path':str(prefix/rel),'reason':'derived retrieval or external capture cache'});continue
                if path.name.startswith('private-'):
                    omitted.append({'path':str(prefix/rel),'reason':'explicitly private working file'});continue
                data=path.read_bytes();text=data.decode('utf-8-sig')
                if path.suffix=='.json':
                    parsed=json.loads(text);clean,found=tree(parsed)
                    output=(json.dumps(clean,ensure_ascii=False,indent=2)+'\n').encode() if found else data
                else:
                    clean,found=sanitize(text);output=clean.encode() if found else data
                dest=DEST/prefix/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(output)
                manifest.append({'path':str((prefix/rel).as_posix()),'source_sha256':sha(data),'public_sha256':sha(output),
                    'bytes':len(output),'byte_identical':output==data,'redactions':len(found)})
                if found:findings.append({'path':str((prefix/rel).as_posix()),'findings':found})
    for name,value in [('document-files.json',manifest),('omitted-working-files.json',omitted),('document-redactions.json',findings)]:
        path=DEST/'publication'/name;path.parent.mkdir(exist_ok=True,parents=True)
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'copied_files':len(manifest),'bytes':sum(x['bytes'] for x in manifest),'redacted_files':len(findings),'omitted_working_files':len(omitted)},ensure_ascii=False))

if __name__=='__main__':main()
