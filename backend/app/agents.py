"""Coordinated LangGraph workflow. All findings derive from scoped application records."""
from typing import TypedDict, Any
from datetime import date
import time, os, httpx
from langgraph.graph import StateGraph, END
from .database import records, add, now

NAMES=['Orchestrator','Traceability','Batch Verification','Counterfeit Detection','Shipment Monitoring','Cold Chain Monitoring','Risk Assessment','Investigation','Compliance & Policy','Report Generation']
class State(TypedDict, total=False):
    db: Any
    org: str
    serial: str
    location: str
    task: str
    manufacturer: str
    batch_number: str
    product: dict
    batch: dict
    shipments: list
    events: list
    evidence: list
    history: list
    risk: int
    status: str
    explanation: str
    recommendation: str
    error: str

def evidence(s, check, passed, detail, weight=0):
    s['evidence'].append({'check':check,'passed':passed,'detail':detail,'weight':0 if passed else weight})
def orchestrate(s):
    s.update(evidence=[],history=[],risk=0)
    serials=records(s['db'],'serials',s['org'])
    s['product']=next((r for r in serials if r['serial']==s['serial']),{})
    s['batch']=next((r for r in records(s['db'],'batches',s['org']) if r['id']==s['product'].get('batch_id')), {})
    s['events']=[r for r in records(s['db'],'events',s['org']) if r['serial']==s['serial']]
    s['shipments']=[r for r in records(s['db'],'shipments',s['org']) if r['batch_id']==s['batch'].get('id')]
    evidence(s,'Registered identifier',bool(s['product']),'Identifier matched registry' if s['product'] else 'No matching record; authenticity is unverified',40)
    return s
def trace(s):
    stages={r['stage'] for r in s['events']}
    evidence(s,'Chain of custody',len(stages)>=4,f'{len(stages)} distinct stages recorded',15)
    return s
def batch(s):
    b=s['batch']
    evidence(s,'Batch registration',bool(b),'Matched '+b.get('batch_number','no batch'),25)
    if b:
        evidence(s,'Expiry',b['expiry']>=str(date.today()),'Expiry date: '+b['expiry'],35)
        evidence(s,'Batch status',b['status']=='Active','Batch is '+b['status'],20)
        evidence(s,'Manufacturing dates',b['manufactured']<=str(date.today()) and b['manufactured']<b['expiry'],'Manufacture date '+b['manufactured'],25)
        registered=any(o['name']==b['manufacturer'] and o['type']=='Manufacturer' for o in records(s['db'],'organizations',s['org']))
        evidence(s,'Manufacturer registry',registered,'Compared with synthetic organization registry',20)
        if s.get('manufacturer'): evidence(s,'Manufacturer match',s['manufacturer'].casefold()==b['manufacturer'].casefold(),'Submitted: '+s['manufacturer']+'; registered: '+b['manufacturer'],30)
        if s.get('batch_number'): evidence(s,'Batch match',s['batch_number']==b['batch_number'],'Submitted: '+s['batch_number']+'; registered: '+b['batch_number'],30)
    return s
def counterfeit(s):
    previous=[r for r in records(s['db'],'verifications',s['org']) if r['serial']==s['serial']]
    # Repeated checks alone do not imply a clone. Distinct locations within one hour do.
    from datetime import datetime, timezone
    recent=[r for r in previous if (datetime.now(timezone.utc)-datetime.fromisoformat(r['created_at'])).total_seconds()<3600]
    locations={r.get('location','') for r in recent if r.get('location')}
    duplicate=bool(s.get('location') and locations and s['location'] not in locations)
    evidence(s,'Identifier usage',not duplicate,f'{len(previous)} prior checks; recent locations: '+(', '.join(sorted(locations)) or 'none'),35)
    evidence(s,'Verification frequency',len(recent)<8,f'{len(recent)} checks in the last hour',15)
    return s
def shipment(s):
    for r in s['shipments']:
        evidence(s,'Shipment route',not r.get('route_deviation'),r['reference']+': '+r['origin']+' → '+r['destination'],20)
        evidence(s,'Delivery schedule',r['status']=='Delivered' or r['expected_delivery']>=str(date.today()),r['reference']+': '+r['status'],10)
    return s
def cold(s):
    readings=records(s['db'],'temperatures',s['org'])
    for r in s['shipments']:
        values=[v for v in readings if v['shipment_id']==r['id']]
        failures=[v for v in values if not r['min_temp']<=v['temperature']<=r['max_temp']]
        evidence(s,'Temperature limits',not failures,f"{r['reference']}: {len(failures)}/{len(values)} readings outside {r['min_temp']}–{r['max_temp']}°C",30)
        evidence(s,'Temperature records',bool(values),f'{len(values)} readings available',10)
    return s
def risk(s):
    s['risk']=min(100,sum(e['weight'] for e in s['evidence']))
    if not s['product']: status='Unverified'
    elif s['batch'] and s['batch']['expiry']<str(date.today()): status='Expired'
    elif any(e['check']=='Identifier usage' and not e['passed'] for e in s['evidence']): status='Duplicate Identifier'
    elif s['risk']>=60: status='Potential Counterfeit'
    elif s['risk']>=30: status='Suspicious'
    else: status='Verified'
    s['status']=status
    failures=[e['detail'] for e in s['evidence'] if not e['passed']]
    s['explanation']='; '.join(failures) if failures else 'Registered identifier, batch and available custody records matched. No configured anomaly rules triggered.'
    s['recommendation']='Request authorized human investigation; do not use this assessment to authorize release, recall or destruction.' if s['risk']>=30 else 'Continue routine handling under approved organizational policies.'
    return s
def investigate(s):
    evidence(s,'Human decision boundary',True,'Agent recommendations cannot execute regulated actions')
    return s
def compliance(s):
    policies=records(s['db'],'policies',s['org'])
    evidence(s,'Configured policies',bool(policies),f'{len(policies)} internal handling policies retrieved. This is not a regulatory certification.',5)
    return s
def report(s):
    if os.getenv('OPENAI_API_KEY'):
        try:
            response=httpx.post('https://api.openai.com/v1/chat/completions',headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},json={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),'messages':[{'role':'system','content':'Summarize supplied synthetic evidence in 3 sentences. Never assert confirmed counterfeit or authorize regulated actions. Do not add facts.'},{'role':'user','content':str(s['evidence'])}]},timeout=15)
            response.raise_for_status(); s['explanation']=response.json()['choices'][0]['message']['content']
        except Exception: s['history'].append({'agent':'LLM explanation','status':'Fallback','detail':'Provider unavailable; using evidence summary'})
    return s
FUNCS=[orchestrate,trace,batch,counterfeit,shipment,cold,risk,investigate,compliance,report]
def wrapped(name, fn):
    def run(s):
        start=time.perf_counter()
        try:
            s=fn(s)
            entry={'agent':name,'status':'Completed','duration_ms':round((time.perf_counter()-start)*1000,2),'timestamp':now()}
        except Exception as exc:
            entry={'agent':name,'status':'Failed','duration_ms':round((time.perf_counter()-start)*1000,2),'timestamp':now(),'detail':str(exc)[:200]}
            s['error']='An agent failed; assessment requires manual review.'
        s.setdefault('history',[]).append(entry)
        return s
    return run
graph=StateGraph(State)
for name,fn in zip(NAMES,FUNCS): graph.add_node(name,wrapped(name,fn))
graph.set_entry_point(NAMES[0])
graph.add_conditional_edges(NAMES[0],lambda s: 'Shipment Monitoring' if s.get('task')=='shipment' else 'Traceability')
for a,b in [(1,2),(2,3),(3,4),(4,5),(5,6)]: graph.add_edge(NAMES[a],NAMES[b])
graph.add_conditional_edges('Risk Assessment',lambda s:'Investigation' if s['risk']>=30 else 'Compliance & Policy')
graph.add_edge('Investigation','Compliance & Policy'); graph.add_edge('Compliance & Policy','Report Generation'); graph.add_edge('Report Generation',END)
workflow=graph.compile()
def execute(db,org,serial,location='',task='verify',**kwargs):
    result=workflow.invoke({'db':db,'org':org,'serial':serial,'location':location,'task':task,**kwargs})
    safe={k:v for k,v in result.items() if k not in ['db','org']}
    if result.get('error'):
        safe['status']='Unverified'; safe['recommendation']='Manual review required because workflow execution was incomplete.'
    add(db,'executions',safe,org)
    return safe
