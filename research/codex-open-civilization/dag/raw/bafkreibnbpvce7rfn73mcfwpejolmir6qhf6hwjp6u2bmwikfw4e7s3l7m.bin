"""Finite synthetic admission experiment; effects are fixture facts, not predictions."""
import copy
import hashlib
import json
import random
from pathlib import Path

HERE=Path(__file__).resolve().parent
CAPS={'alice':10,'bob':10}
GRANTS={'alice':{'epoch':2,'active':True},'bob':{'epoch':3,'active':True}}

class Candidate:
    def __init__(self,mode,caps,grants):
        self.mode=mode; self.caps=copy.deepcopy(caps); self.grants=copy.deepcopy(grants)
        self.reserved={k:0 for k in caps}; self.seen=set(); self.checks=0
    def admit(self,request,modeled_effect):
        declared=request['declared']
        self.checks+=1
        if not declared or any(k not in self.caps or type(v) is not int or v<=0 for k,v in declared.items()):
            return False
        if self.mode=='C':
            self.checks+=2
            if request['id'] in self.seen or declared!=modeled_effect: return False
        for owner,amount in declared.items():
            self.checks+=1
            if self.mode=='A':
                if amount>self.caps[owner]:return False
            else:
                self.checks+=2
                grant=self.grants[owner]
                if not grant['active'] or request['epochs'].get(owner)!=grant['epoch']:return False
                if self.reserved[owner]+amount>self.caps[owner]:return False
        for owner,amount in declared.items():self.reserved[owner]+=amount
        if self.mode=='C':self.seen.add(request['id'])
        return True

def action(name,declared,effect=None,epochs=None):
    return {'id':name,'declared':declared,'effect':declared.copy() if effect is None else effect,
            'epochs':{'alice':2,'bob':3} if epochs is None else epochs}

def fixtures():
    result=[
      ('joint-over-cap',[action('a',{'alice':6}),action('b',{'alice':6})],[True,False]),
      ('old-epoch',[action('a',{'alice':3},epochs={'alice':1})],[False]),
      ('repeat-id',[action('a',{'alice':3}),action('a',{'alice':3})],[True,False]),
      ('omitted-owner',[action('a',{'alice':2},effect={'alice':2,'bob':2})],[False]),
      ('valid-boundary',[action('a',{'alice':10,'bob':10})],[True]),
      ('empty',[action('a',{})],[False]),
      ('zero',[action('a',{'alice':0})],[False]),
      ('negative',[action('a',{'alice':-1})],[False]),
      ('unknown-owner',[action('a',{'carol':2})],[False]),
      ('inactive',[action('a',{'alice':2})],[False]),
      ('scope-amount-mismatch',[action('a',{'alice':2},effect={'alice':9})],[False]),
      ('two-valid-actions',[action('a',{'alice':3}),action('b',{'alice':4,'bob':2})],[True,True])]
    cases=[]
    for name,actions,expected in result:
        grants=copy.deepcopy(GRANTS)
        if name=='inactive':grants['alice']['active']=False
        cases.append({'name':name,'caps':CAPS.copy(),'grants':grants,'actions':actions,'expected_C':expected})
    return cases

def generated(plan):
    rng=random.Random(plan['seed']); result=[]
    for i in range(plan['traces']):
        actions=[]
        for j in range(plan['actions_per_trace']):
            who=rng.choice(['alice','bob']); amount=rng.randint(1,8)
            declared={who:amount}; effect=declared.copy(); epochs={'alice':2,'bob':3}
            kind=rng.randrange(7); identity=f'{i}-{j}'
            if kind==1:epochs[who]-=1
            elif kind==2 and actions: identity=actions[rng.randrange(len(actions))]['id']
            elif kind==3:effect['bob' if who=='alice' else 'alice']=rng.randint(1,4)
            elif kind==4:effect[who]+=rng.randint(1,3)
            elif kind==5:declared[who]=0;effect=declared.copy()
            elif kind==6:epochs[who]+=1
            actions.append(action(identity,declared,effect,epochs))
        result.append({'name':f'generated-{i:03d}','caps':CAPS.copy(),'grants':copy.deepcopy(GRANTS),'actions':actions})
    return result

def check_history(case,history):
    # Oracle rebuilds effects from fixture data; it does not read candidate counters.
    spent={k:0 for k in case['caps']}; seen=set(); failures=[]
    for step in history:
        if not step['accepted']:
            assert step['applied_effect']=={}
            continue
        a=case['actions'][step['index']]; problems=[]
        if not a['effect'] or any(k not in spent or type(v) is not int or v<=0 for k,v in a['effect'].items()):
            problems.append('invalid-effect')
        if a['id'] in seen:problems.append('replayed-request')
        seen.add(a['id'])
        if a['declared']!=a['effect']:problems.append('scope-mismatch')
        for owner,amount in a['effect'].items():
            g=case['grants'].get(owner)
            if not g or not g['active'] or a['epochs'].get(owner)!=g['epoch']:problems.append('invalid-current-grant:'+owner)
            if owner in spent:
                spent[owner]+=amount
                if spent[owner]>case['caps'][owner]:problems.append('cap-exceeded:'+owner)
        if problems:failures.append({'index':step['index'],'problems':problems,'spent_after':spent.copy()})
    return failures

def run_case(case,mode):
    candidate=Candidate(mode,case['caps'],case['grants']); history=[]
    for i,a in enumerate(case['actions']):
        accepted=candidate.admit(a,a['effect'])
        history.append({'index':i,'accepted':accepted,'applied_effect':a['effect'] if accepted else {}})
    failures=check_history(case,history)
    return {'case':case['name'],'candidate':mode,'history':history,'failures':failures,
            'admitted':sum(x['accepted'] for x in history),'check_operations':candidate.checks,
            'retained_request_ids':len(candidate.seen)}

def write(path,obj):path.write_bytes((json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode())

def main():
    destination=HERE/'run-01'
    destination.mkdir(exist_ok=False)
    plan=json.loads((HERE/'pre-registration.json').read_bytes())
    fixed=fixtures(); random_cases=generated(plan['generated_cases']); cases=fixed+random_cases
    write(destination/'inputs.json',cases)
    outputs=[run_case(case,mode) for mode in 'ABC' for case in cases]
    write(destination/'results.json',outputs)
    aggregate={}
    for mode in 'ABC':
        rows=[r for r in outputs if r['candidate']==mode]
        aggregate[mode]={'traces':len(rows),'failing_traces':sum(bool(r['failures']) for r in rows),
            'admitted_actions':sum(r['admitted'] for r in rows),'check_operations':sum(r['check_operations'] for r in rows),
            'maximum_retained_request_ids_in_one_trace':max(r['retained_request_ids'] for r in rows)}
    c_rows=[r for r in outputs if r['candidate']=='C']
    assert not any(r['failures'] for r in c_rows),'Retain run-01 and repair in a new version.'
    for case,row in zip(cases,c_rows):
        if 'expected_C' in case:assert [x['accepted'] for x in row['history']]==case['expected_C'],case['name']
    assert aggregate['A']['failing_traces']>0 and aggregate['B']['failing_traces']>0
    report={'status':'completed','pre_registration_sha256':hashlib.sha256((HERE/'pre-registration.json').read_bytes()).hexdigest(),
        'program_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixed_cases':len(fixed),
        'generated_traces':len(random_cases),'actions_per_candidate':sum(len(c['actions']) for c in cases),
        'results':aggregate,'positive_acceptance_controls':'pass',
        'scope':'Synthetic sequential admission with true effect scope supplied by fixtures. No privacy, human fairness, economic sustainability, physical loss or distributed-consensus claims.',
        'cost_boundary':'check_operations are counted Python-level predicate groups, not time or energy. Inputs and verification costs are also required; no efficiency ranking is claimed.'}
    write(destination/'summary.json',report)
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
