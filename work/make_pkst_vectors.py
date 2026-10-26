import sys,json
from pathlib import Path
root=Path(r'C:\Users\langr\Documents\Codex\2026-10-24\ni\outputs\personal-thought-archive')
sys.path.insert(0,str(root/'contributions/codex'))
from pkst_codec import encode,cid,link,linkset,MAX_INT
cases=[('null',None,'f6'),('true',True,'f5'),('false',False,'f4'),('int23',23,'17'),('int24',24,'1818'),('negative25',-25,'3818'),('empty-map',{},'a0'),('map-order',{'aa':2,'b':1},'a261620162616102'),('unicode','思想\r\ne\u0301',None),('max-int',MAX_INT,None),('min-int',-MAX_INT,None),('raw-link',link(cid(b'hello',0x55)),None)]
actor={'kind':'ai','id':'codex'}
source={'schema':'pkst/source@0.1','platform':'synthetic','namespace':'test-owner','native_thread_id':'t1'}
s=cid(encode(source));content={'schema':'pkst/content@0.1','media_type':'text/plain; charset=utf-8','text':'如果 A，那么 B？\r\n'};c=cid(encode(content))
occ={'schema':'pkst/occurrence@0.1','source':link(s),'native_id':'m1','locator':None,'native_role':'user','actor_kind':'unknown','process_kind':'main','content':[link(c)],'native_parent_ids':[],'event_time':{'value':None,'precision':'unknown','zone_known':False}}
o=cid(encode(occ))
objects=[source,content,occ,{'schema':'pkst/concept@0.1','label':'测试','definition':'测试概念','evidence':linkset([o]),'asserted_by':actor},{'schema':'pkst/statement@0.1','text':'如果 A，那么 B？','force':'question','holder':{'kind':'unknown','id':'unknown'},'evidence':linkset([o]),'asserted_by':actor,'lineage':None}]
st=cid(encode(objects[-1]))
objects.extend([{'schema':'pkst/relation@0.1','predicate':'propagation-candidate','from':link(o),'to':link(st),'evidence':linkset([o]),'asserted_by':actor,'basis':'inferred','scope':'synthetic only'},{'schema':'pkst/change@0.1','operation':'revise','from_versions':linkset([st]),'to_versions':[],'evidence':linkset([o]),'asserted_by':actor,'basis':'unknown','reason':'candidate'},{'schema':'pkst/assessment@0.1','target':link(st),'judgment':'uncertain','asserted_by':actor,'evidence':linkset([o]),'recorded_at':'2026-10-24T00:00:00Z'},{'schema':'pkst/activity@0.1','operation':'observe','recorded_at':'2026-10-24T00:00:00Z','actor':actor,'inputs':linkset([o]),'outputs':linkset([st]),'implementation':'fixture','coverage':{'status':'synthetic'}},{'schema':'pkst/snapshot@0.1','parents':[],'roots':linkset([o,st]),'coverage':{'status':'synthetic'},'protocol':'PKST-0.1'},{'schema':'pkst/extraction-record@0.1','raw':link(cid(b'hello',0x55)),'occurrence':link(o),'start':0,'end':5,'coordinate':'decoded-jsonl-utf8-bytes','parser':'fixture','role_basis':'unknown'}])
cases.extend((o['schema'],o,None) for o in objects)
result=[]
for name,obj,golden in cases:
    b=encode(obj)
    if golden is not None:assert b.hex()==golden
    result.append({'name':name,'value':obj,'cbor_hex':b.hex(),'cid':cid(b)})
rejected=[{'name':'float','value':0.5},{'name':'overflow','value':MAX_INT+1},{'name':'surrogate','value':'\ud800'},{'name':'invalid-link','value':{'$link':'bad'}},{'name':'reserved-map','value':{'$link':cid(b'hello',0x55),'other':1}}]
for v in rejected:
    try:encode(v['value'])
    except (ValueError,UnicodeError):pass
    else:raise AssertionError(v['name'])
out={'schema':'pkst.test-vectors.v0.1','positive':result,'negative':rejected,'negative_json':['{"x":1,"x":2}'],'notes':'Static codec vectors. Synthetic examples test encoding, not semantic validity of their assertions.'}
(root/'protocol/test-vectors.json').write_text(json.dumps(out,ensure_ascii=True,indent=2),encoding='utf-8')
print(json.dumps({'positive':len(result),'negative':len(rejected)+1,'manual_hex_controls':8,'status':'codex-pass-independent-peer-pending'}))
