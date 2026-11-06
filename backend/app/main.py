import os, re, io, csv, time, secrets, json
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from .database import *
from .security import *
from .seed import seed
from .agents import execute, NAMES

Base.metadata.create_all(engine)
with Session() as db:
    if DEMO: seed(db)
app=FastAPI(title='PharmaTrace AI',version='1.0.0',description='Synthetic demonstration; assessments are not laboratory confirmations.')
origins=os.getenv('ALLOWED_ORIGINS','http://localhost:3000').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['GET','POST','PUT','PATCH'],allow_headers=['Authorization','Content-Type'])
@app.post('/api/ml/predict')
def ml_predict(body:dict,user=Depends(current)):
    from .ml import predict
    return predict(body)
@app.middleware('http')
async def security_headers(request, call_next):
    if request.method not in ['GET','HEAD','OPTIONS'] and request.cookies.get('pt_session'):
        from urllib.parse import urlparse
        origin=request.headers.get('origin')
        if origin and urlparse(origin).netloc!=request.headers.get('host'):
            return JSONResponse({'detail':'Cross-origin mutation rejected'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response
class Credentials(BaseModel):
    email:str=Field(min_length=5,max_length=180)
    password:str=Field(min_length=8,max_length=128)
    name:str=Field(default='New user',min_length=1,max_length=100)
    @field_validator('email')
    @classmethod
    def valid_email(cls,v):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v): raise ValueError('Valid email required')
        return v.lower()
class Verify(BaseModel):
    serial:str=Field(min_length=3,max_length=120)
    location:str=Field(default='',max_length=100)
    manufacturer:str=Field(default='',max_length=120)
    batch_number:str=Field(default='',max_length=80)
    task:str=Field(default='verify',max_length=40)
class AgentRequest(BaseModel):
    serial:str=Field(default='PT-2026-000003',max_length=120)
    task:str=Field(default='verify',max_length=40)
    message:str=Field(default='',max_length=2000)
class ProductInput(BaseModel):
    name:str=Field(min_length=2,max_length=150)
    manufacturer:str=Field(min_length=2,max_length=120)
    category:str=Field(default='General medicine',max_length=80)
    min_temp:float=15
    max_temp:float=30
    barcode:str=Field(default='',max_length=100)
class BatchInput(BaseModel):
    batch_number:str=Field(min_length=3,max_length=80)
    product_id:str
    manufactured:date
    expiry:date
    quantity:int=Field(gt=0,le=10000000)
class ShipmentInput(BaseModel):
    batch_id:str
    origin:str=Field(min_length=2,max_length=100)
    destination:str=Field(min_length=2,max_length=100)
    quantity:int=Field(gt=0,le=1000000)
    expected_delivery:date
class Note(BaseModel):
    text:str=Field(min_length=3,max_length=4000)
class Approval(BaseModel):
    action:str=Field(pattern='^(quarantine|release|recall|destruction)$')
    decision:str=Field(pattern='^(approved|rejected)$')
    reason:str=Field(min_length=10,max_length=2000)
class InvestigationInput(BaseModel):
    title:str=Field(min_length=3,max_length=160)
    serial:str=Field(min_length=3,max_length=120)
class StatusUpdate(BaseModel):
    status:str=Field(min_length=2,max_length=50)
    reason:str=Field(default='',max_length=1000)
    assigned_to:str=Field(default='',max_length=120)

def get_record(db,kind,id,user):
    r=db.query(Record).filter_by(id=id,kind=kind,org=user['org']).first()
    if not r: raise HTTPException(404,'Record not found')
    return r
def identity(u): return {'id':u.id,'email':u.email,'name':u.name,'role':u.role,'org':u.org}
def session_response(payload):
    response=JSONResponse(payload)
    response.set_cookie('pt_session',payload['token'],httponly=True,secure=bool(os.getenv('VERCEL')),samesite='lax',max_age=28800,path='/')
    return response
@app.post('/api/auth/logout')
def logout():
    response=JSONResponse({'ok':True});response.delete_cookie('pt_session',path='/');return response
rate={}
def limited(key, count=30):
    tick=int(time.time()//60); bucket=(key,tick)
    rate[bucket]=rate.get(bucket,0)+1
    if len(rate)>10000: rate.clear()
    if rate.get(bucket,0)>count: raise HTTPException(429,'Too many requests. Retry in one minute.')
@app.get('/health')
@app.get('/api/health')
def health(): return {'status':'ok','demo':DEMO,'persistence':'ephemeral' if os.getenv('VERCEL') and 'sqlite' in url else 'database','engine':'LangGraph + evidence rules'}
@app.post('/api/auth/demo')
def demo(request:Request, db=Depends(get_db)):
    if not DEMO: raise HTTPException(403,'Demo access disabled')
    limited('demo:'+str(request.client.host),15)
    # Each demo session receives an isolated organization and dataset.
    org='demo-'+secrets.token_hex(8); seed(db,org)
    u={'id':uid(),'email':'demo@example.test','name':'Alex Morgan','role':'System Administrator','org':org}
    return session_response({'token':token(u),'user':u,'demo':True})
@app.post('/api/auth/register')
def register(body:Credentials,request:Request,db=Depends(get_db)):
    limited('register:'+str(request.client.host),5)
    supabase_session=None
    if os.getenv('SUPABASE_URL'):
        response=httpx.post(os.environ['SUPABASE_URL']+'/auth/v1/signup',headers={'apikey':os.environ['SUPABASE_ANON_KEY']},json={'email':body.email,'password':body.password},timeout=15)
        if response.status_code>=400: raise HTTPException(400,'Registration failed. Check email or account configuration.')
        supabase_session=response.json().get('access_token')
    if db.query(User).filter_by(email=body.email).first(): raise HTTPException(409,'Account already exists')
    org='org-'+uid()
    u=User(email=body.email,password=password_hash(body.password),name=body.name,org=org,role='Pharmacist');db.add(u);db.flush()
    if DEMO: seed(db,org)
    if os.getenv('SUPABASE_URL'):
        if supabase_session: return session_response({'token':supabase_session,'user':identity(u),'demo':False})
        return {'confirmation_required':True,'message':'Check your email to confirm your account, then sign in.'}
    return session_response({'token':token(identity(u)),'user':identity(u),'demo':DEMO})
@app.post('/api/auth/login')
def login(body:Credentials,request:Request,db=Depends(get_db)):
    limited('login:'+str(request.client.host),10)
    u=db.query(User).filter_by(email=body.email).first()
    if os.getenv('SUPABASE_URL'):
        response=httpx.post(os.environ['SUPABASE_URL']+'/auth/v1/token?grant_type=password',headers={'apikey':os.environ['SUPABASE_ANON_KEY']},json={'email':body.email,'password':body.password},timeout=15)
        if response.status_code>=400 or not u: raise HTTPException(401,'Invalid credentials')
        return session_response({'token':response.json()['access_token'],'user':identity(u),'demo':False})
    if not u or not password_check(body.password,u.password): raise HTTPException(401,'Invalid credentials')
    return session_response({'token':token(identity(u)),'user':identity(u),'demo':DEMO})
@app.get('/api/auth/me')
def me(user=Depends(current)): return user
@app.get('/api/data')
def data(user=Depends(current),db=Depends(get_db)):
    kinds=['products','batches','serials','organizations','shipments','temperatures','events','verifications','alerts','investigations','executions','inventory','audit','reports','policies','inventory_transactions']
    return {k:records(db,k,user['org']) for k in kinds}
@app.get('/api/products')
def products(user=Depends(current),db=Depends(get_db)): return records(db,'products',user['org'])
@app.post('/api/products')
def create_product(body:ProductInput,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Manufacturer'])
    if body.min_temp>=body.max_temp: raise HTTPException(422,'Minimum temperature must be below maximum')
    r=add(db,'products',dict(body.model_dump(),status='Registered'),user['org']);audit(db,user,'Register product',r['id']);return r
@app.get('/api/products/{id}')
def product(id:str,user=Depends(current),db=Depends(get_db)): return get_record(db,'products',id,user).data
@app.put('/api/products/{id}')
def edit_product(id:str,body:ProductInput,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Manufacturer']);r=get_record(db,'products',id,user)
    if body.min_temp>=body.max_temp: raise HTTPException(422,'Invalid temperature limits')
    r.data=dict(r.data,**body.model_dump());audit(db,user,'Update product',id);return r.data
@app.get('/api/batches')
def batches(user=Depends(current),db=Depends(get_db)): return records(db,'batches',user['org'])
@app.post('/api/batches')
def create_batch(body:BatchInput,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Manufacturer']);p=get_record(db,'products',body.product_id,user)
    if body.manufactured>date.today() or body.expiry<=body.manufactured: raise HTTPException(422,'Invalid manufacturing or expiry dates')
    if any(b['batch_number']==body.batch_number for b in records(db,'batches',user['org'])): raise HTTPException(409,'Batch number already registered')
    r=add(db,'batches',dict(body.model_dump(mode='json'),product=p.data['name'],manufacturer=p.data['manufacturer'],min_temp=p.data['min_temp'],max_temp=p.data['max_temp'],quality='Pending',status='Active'),user['org']);audit(db,user,'Create batch',r['id']);return r
@app.get('/api/batches/{id}')
def batch_detail(id:str,user=Depends(current),db=Depends(get_db)): return dict(get_record(db,'batches',id,user).data,id=id)
@app.post('/api/batches/{id}/serialize')
def serialize(id:str,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Manufacturer']);b=get_record(db,'batches',id,user);serial='PT-'+secrets.token_hex(8).upper()
    r=add(db,'serials',{'serial':serial,'batch_id':id,'product_id':b.data['product_id'],'product':b.data['product'],'status':'Unverified'},user['org'])
    add(db,'events',{'serial':serial,'batch_id':id,'stage':'Serialized','organization':user['org'],'location':'Registered facility','timestamp':now(),'responsible_user':user['email'],'status':'Recorded'},user['org']);audit(db,user,'Serialize product',serial);return r
@app.post('/api/verification/verify')
@app.post('/api/counterfeit/analyze')
def verify(body:Verify,user=Depends(current),db=Depends(get_db)):
    limited('verify:'+user['id'])
    serial=body.serial.strip()
    if serial.startswith('PHARMATRACE:'): serial=serial.split(':',1)[1]
    if not re.fullmatch(r'[A-Za-z0-9-]{3,80}',serial): raise HTTPException(422,'Invalid serial or PharmaTrace QR payload')
    result=execute(db,user['org'],serial,body.location,body.task,manufacturer=body.manufacturer,batch_number=body.batch_number)
    record=add(db,'verifications',dict(result,location=body.location,product=result['product'].get('product','Unknown identifier')),user['org'])
    if result['risk']>=30:
        add(db,'alerts',{'title':result['status']+': '+serial,'category':'Verification','priority':'Critical' if result['risk']>=80 else 'High','status':'Open','serial':serial},user['org'])
        if not any(i['serial']==serial and i['status']!='Resolved' for i in records(db,'investigations',user['org'])):
            add(db,'investigations',{'title':'Investigate '+serial,'serial':serial,'risk':result['risk'],'status':'New','assigned_to':'Unassigned','notes':[],'approvals':[],'evidence':result['evidence'],'recommendation':result['recommendation']},user['org'])
    audit(db,user,'Verify medicine',serial,result['status']); return record
@app.get('/api/verification/history')
def history(user=Depends(current),db=Depends(get_db)): return records(db,'verifications',user['org'])
@app.get('/api/verification/{id}')
def verification_detail(id:str,user=Depends(current),db=Depends(get_db)): return dict(get_record(db,'verifications',id,user).data,id=id)
@app.get('/api/traceability/batch/{id}')
def trace_batch(id:str,user=Depends(current),db=Depends(get_db)): return [r for r in records(db,'events',user['org']) if r['batch_id']==id]
@app.get('/api/traceability/{serial}')
def trace_serial(serial:str,user=Depends(current),db=Depends(get_db)): return [r for r in records(db,'events',user['org']) if r['serial']==serial]
@app.get('/api/shipments')
def shipments(user=Depends(current),db=Depends(get_db)): return records(db,'shipments',user['org'])
@app.post('/api/shipments')
def create_shipment(body:ShipmentInput,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Distributor','Warehouse Manager']);b=get_record(db,'batches',body.batch_id,user)
    r=add(db,'shipments',dict(body.model_dump(mode='json'),reference='SHP-'+secrets.token_hex(3).upper(),product=b.data['product'],status='Dispatched',location=body.origin,min_temp=b.data['min_temp'],max_temp=b.data['max_temp'],route_deviation=False),user['org'])
    add(db,'inventory_transactions',{'shipment_id':r['id'],'batch_id':body.batch_id,'quantity':body.quantity,'origin':body.origin,'destination':body.destination,'type':'Dispatch'},user['org']);audit(db,user,'Create shipment',r['id']);return r
@app.get('/api/shipments/{id}')
def shipment_detail(id:str,user=Depends(current),db=Depends(get_db)): return dict(get_record(db,'shipments',id,user).data,id=id)
@app.put('/api/shipments/{id}')
def update_shipment(id:str,body:StatusUpdate,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Distributor','Warehouse Manager'])
    if body.status not in ['Dispatched','In transit','Delayed','Delivered']: raise HTTPException(422,'Invalid shipment status')
    r=get_record(db,'shipments',id,user);r.data=dict(r.data,status=body.status)
    add(db,'shipment_tracking_events',{'shipment_id':id,'status':body.status,'actor':user['email'],'reason':body.reason},user['org'])
    if body.status=='Delivered': add(db,'inventory_transactions',{'shipment_id':id,'batch_id':r.data['batch_id'],'quantity':r.data['quantity'],'type':'Receipt','location':r.data['destination']},user['org'])
    audit(db,user,'Shipment '+body.status,id);return r.data
class Temperature(BaseModel):
    temperature:float=Field(ge=-100,le=100)
@app.post('/api/shipments/{id}/temperature')
def temperature(id:str,body:Temperature,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Distributor','Warehouse Manager']);r=get_record(db,'shipments',id,user)
    v=add(db,'temperatures',{'shipment_id':id,'temperature':body.temperature,'timestamp':now()},user['org'])
    if not r.data['min_temp']<=body.temperature<=r.data['max_temp']: add(db,'alerts',{'title':'Temperature excursion: '+r.data['reference'],'category':'Cold chain','priority':'High','status':'Open'},user['org'])
    audit(db,user,'Record temperature',id,str(body.temperature));return v
@app.get('/api/agents')
def agents(user=Depends(current),db=Depends(get_db)):
    executions=records(db,'executions',user['org']);out=[]
    for name in NAMES:
        runs=[h for e in executions for h in e.get('history',[]) if h['agent']==name]
        out.append({'name':name,'completed':sum(h['status']=='Completed' for h in runs),'failed':sum(h['status']=='Failed' for h in runs),'last_execution':runs[0]['timestamp'] if runs else None,'average_ms':round(sum(h['duration_ms'] for h in runs)/len(runs),2) if runs else 0})
    return out
@app.get('/api/agents/executions')
def executions(user=Depends(current),db=Depends(get_db)): return records(db,'executions',user['org'])
@app.post('/api/agents/run')
def agent_run(body:AgentRequest,user=Depends(current),db=Depends(get_db)):
    limited('agent:'+user['id'],15)
    serial=body.serial
    match=re.search(r'PT-[A-Za-z0-9-]+',body.message)
    if match: serial=match.group()
    task='shipment' if any(w in body.message.lower() for w in ['shipment','cold','temperature']) else body.task
    result=execute(db,user['org'],serial,task=task);audit(db,user,'Run agent workflow',serial,task);return result
@app.get('/api/investigations')
def investigations(user=Depends(current),db=Depends(get_db)): return records(db,'investigations',user['org'])
@app.post('/api/investigations')
def create_investigation(body:InvestigationInput,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Investigator','Compliance Officer']);r=add(db,'investigations',dict(body.model_dump(),status='New',assigned_to='Unassigned',risk=0,notes=[],evidence=[],approvals=[]),user['org']);audit(db,user,'Open investigation',r['id']);return r
@app.get('/api/investigations/{id}')
def investigation_detail(id:str,user=Depends(current),db=Depends(get_db)): return dict(get_record(db,'investigations',id,user).data,id=id)
@app.post('/api/investigations/{id}/notes')
def add_note(id:str,body:Note,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Investigator','Compliance Officer']);r=get_record(db,'investigations',id,user)
    r.data=dict(r.data,notes=r.data.get('notes',[])+[{'text':body.text,'actor':user['email'],'timestamp':now()}]);audit(db,user,'Add investigation note',id);return r.data
@app.put('/api/investigations/{id}')
def update_investigation(id:str,body:StatusUpdate,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Investigator','Compliance Officer'])
    if body.status not in ['New','Under Investigation','Awaiting Approval','Resolved','Escalated']: raise HTTPException(422,'Invalid investigation status')
    if body.status=='Resolved' and len(body.reason)<10: raise HTTPException(422,'Document a resolution reason of at least 10 characters')
    r=get_record(db,'investigations',id,user);r.data=dict(r.data,status=body.status,assigned_to=body.assigned_to or r.data.get('assigned_to'),resolution=body.reason);audit(db,user,'Investigation '+body.status,id,body.reason);return r.data
@app.post('/api/investigations/{id}/approval')
def approval(id:str,body:Approval,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Compliance Officer']);r=get_record(db,'investigations',id,user)
    decision=dict(body.model_dump(),actor=user['email'],timestamp=now(),scope='Recorded human decision only; no physical or regulatory action executed')
    r.data=dict(r.data,approvals=r.data.get('approvals',[])+[decision]);add(db,'human_approvals',dict(decision,investigation_id=id),user['org']);audit(db,user,'Human '+body.decision,id,body.reason);return r.data
@app.post('/api/investigations/{id}/evidence')
async def upload_evidence(id:str,file:UploadFile=File(...),user=Depends(current),db=Depends(get_db)):
    allowed(user,['Investigator','Compliance Officer']);r=get_record(db,'investigations',id,user)
    content=await file.read(1048577)
    if len(content)>1048576: raise HTTPException(413,'Maximum evidence file size is 1 MB')
    if file.content_type not in ['text/plain','text/csv','application/pdf']: raise HTTPException(415,'Use TXT, CSV or PDF evidence')
    if file.content_type=='application/pdf' and not content.startswith(b'%PDF'): raise HTTPException(422,'Invalid PDF')
    import base64,hashlib
    e={'filename':os.path.basename(file.filename or 'evidence'),'content_type':file.content_type,'size':len(content),'sha256':hashlib.sha256(content).hexdigest(),'content_base64':base64.b64encode(content).decode(),'actor':user['email'],'timestamp':now()}
    add(db,'evidence',dict(e,investigation_id=id),user['org']);r.data=dict(r.data,evidence=r.data.get('evidence',[])+[{k:v for k,v in e.items() if k!='content_base64'}]);audit(db,user,'Upload evidence',id,e['filename']);return {k:v for k,v in e.items() if k!='content_base64'}
@app.get('/api/counterfeit/alerts')
def alerts(user=Depends(current),db=Depends(get_db)): return records(db,'alerts',user['org'])
@app.put('/api/alerts/{id}')
def update_alert(id:str,body:StatusUpdate,user=Depends(current),db=Depends(get_db)):
    allowed(user,['Investigator','Compliance Officer'])
    if body.status not in ['Acknowledged','Resolved']: raise HTTPException(422,'Invalid alert status')
    if body.status=='Resolved' and len(body.reason)<10: raise HTTPException(422,'Resolution reason required')
    r=get_record(db,'alerts',id,user);r.data=dict(r.data,status=body.status,resolution=body.reason);audit(db,user,'Alert '+body.status,id,body.reason);return r.data
@app.get('/api/analytics/dashboard')
@app.get('/api/analytics/risk')
@app.get('/api/analytics/shipments')
def analytics(user=Depends(current),db=Depends(get_db)):
    d=data(user,db);v=d['verifications']
    return {'products':len(d['products']),'batches':len(d['batches']),'shipments':len([s for s in d['shipments'] if s['status']!='Delivered']),'verified':sum(r['status']=='Verified' for r in v),'suspicious':sum(r['risk']>=30 for r in v),'verifications':len(v),'alerts':sum(a['status']!='Resolved' for a in d['alerts']),'investigations':sum(i['status']!='Resolved' for i in d['investigations']),'expired':sum(b['expiry']<str(date.today()) for b in d['batches']),'excursions':sum(not s['min_temp']<=t['temperature']<=s['max_temp'] for s in d['shipments'] for t in d['temperatures'] if t['shipment_id']==s['id'])}
@app.get('/api/users')
def users(user=Depends(current),db=Depends(get_db)):
    allowed(user,[]);return [identity(u) for u in db.query(User).filter_by(org=user['org']).all()]+([user] if user['email']=='demo@example.test' else [])
class RoleInput(BaseModel): role:str
@app.put('/api/users/{id}/role')
def role(id:str,body:RoleInput,user=Depends(current),db=Depends(get_db)):
    allowed(user,[])
    if id==user['id']: raise HTTPException(422,'Cannot modify your own role')
    if body.role not in ['System Administrator','Manufacturer','Distributor','Warehouse Manager','Pharmacist','Hospital Administrator','Compliance Officer','Investigator']: raise HTTPException(422,'Invalid role')
    u=db.query(User).filter_by(id=id,org=user['org']).first()
    if not u: raise HTTPException(404,'User not found')
    u.role=body.role;audit(db,user,'Change role',id,body.role);return identity(u)
@app.get('/api/reports')
def reports(user=Depends(current),db=Depends(get_db)): return records(db,'reports',user['org'])
class ReportInput(BaseModel):
    kind:str=Field(default='verifications',pattern='^(verifications|batches|shipments|events|investigations|audit|inventory|alerts)$')
    format:str=Field(default='csv',pattern='^(csv|pdf)$')
    search:str=Field(default='',max_length=100)
@app.post('/api/reports/generate')
def generate_report(body:ReportInput,user=Depends(current),db=Depends(get_db)):
    rows=[r for r in records(db,body.kind,user['org']) if body.search.lower() in json.dumps(r).lower()]
    add(db,'reports',{'name':body.kind.title()+' report','format':body.format,'records':len(rows),'filters':body.search,'generated_by':user['email']},user['org']);audit(db,user,'Export report',body.kind)
    if body.format=='csv':
        out=io.StringIO();keys=sorted({k for r in rows for k,v in r.items() if not isinstance(v,(dict,list))})
        writer=csv.DictWriter(out,fieldnames=keys,extrasaction='ignore');writer.writeheader()
        for r in rows:
            safe={k:('\''+str(v) if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in r.items()};writer.writerow(safe)
        content=out.getvalue().encode();mime='text/csv'
    else:
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import simpleSplit
        stream=io.BytesIO();c=canvas.Canvas(stream);y=800
        def line(text):
            nonlocal y
            for l in simpleSplit(str(text),'Helvetica',9,500):
                if y<50:c.showPage();y=800;c.setFont('Helvetica',9)
                c.drawString(45,y,l);y-=14
        c.setFont('Helvetica',9);line('PharmaTrace AI | '+body.kind.title()+' | '+now());line('Organization: '+user['org']+' | Filters: '+(body.search or 'All records'));line('SYNTHETIC DEMONSTRATION. Not a laboratory determination or regulatory approval.')
        for r in rows:
            line(' | '.join(f'{k}: {v}' for k,v in r.items() if not isinstance(v,(dict,list))));y-=8
        c.save();content=stream.getvalue();mime='application/pdf'
    return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="pharmatrace-{body.kind}.{body.format}"'})
