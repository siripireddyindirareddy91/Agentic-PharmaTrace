import os
os.environ['DATABASE_URL']='sqlite:///./test-pharmatrace.db'
os.environ['JWT_SECRET']='test-only-key-not-for-production-1234567890'
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import Session, User
from backend.app.security import token
import pytest
client=TestClient(app)
@pytest.fixture(scope='module')
def auth():
    r=client.post('/api/auth/demo');assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}
def test_requires_auth(): assert TestClient(app).get('/api/data').status_code==401
def test_seed_and_metrics(auth):
    d=client.get('/api/data',headers=auth).json()
    assert len(d['products'])==15 and len(d['batches'])==25 and len(d['serials'])==100 and len(d['shipments'])==20 and len(d['events'])>=50
    assert client.get('/api/analytics/dashboard',headers=auth).json()['products']==15
def test_product_and_batch_validation(auth):
    r=client.post('/api/products',headers=auth,json={'name':'Test medicine','manufacturer':'Aster Pharma','min_temp':2,'max_temp':8});assert r.status_code==200
    p=r.json()['id']
    invalid=client.post('/api/batches',headers=auth,json={'batch_number':'BAD-001','product_id':p,'manufactured':'2026-01-01','expiry':'2025-01-01','quantity':10});assert invalid.status_code==422
    good=client.post('/api/batches',headers=auth,json={'batch_number':'TEST-001','product_id':p,'manufactured':'2025-01-01','expiry':'2028-01-01','quantity':10});assert good.status_code==200
    q=client.post('/api/batches/'+good.json()['id']+'/serialize',headers=auth);assert q.status_code==200 and q.json()['serial'].startswith('PT-')
def test_unknown_and_qr(auth):
    r=client.post('/api/verification/verify',headers=auth,json={'serial':'PHARMATRACE:PT-2026-000001','location':'Hyderabad'});assert r.status_code==200 and r.json()['status']=='Verified'
    unknown=client.post('/api/verification/verify',headers=auth,json={'serial':'PT-UNKNOWN'}).json();assert unknown['status']=='Unverified' and unknown['risk']>=40
    assert client.post('/api/verification/verify',headers=auth,json={'serial':'<script>'}).status_code==422
def test_duplicate_detection(auth):
    r=client.post('/api/verification/verify',headers=auth,json={'serial':'PT-2026-000001','location':'Tokyo'}).json();assert r['status']=='Duplicate Identifier'
    assert any(e['check']=='Identifier usage' and not e['passed'] for e in r['evidence'])
def test_expiry(auth):
    r=client.post('/api/verification/verify',headers=auth,json={'serial':'PT-2026-000005'}).json();assert r['status']=='Expired'
def test_cold_and_orchestration(auth):
    r=client.post('/api/agents/run',headers=auth,json={'serial':'PT-2026-000003'}).json()
    assert any(e['check']=='Temperature limits' and not e['passed'] for e in r['evidence'])
    assert len(r['history'])>=9 and all(h['status']=='Completed' for h in r['history'])
    r=client.post('/api/agents/run',headers=auth,json={'serial':'PT-2026-000008','task':'shipment'}).json()
    assert 'Traceability' not in [h['agent'] for h in r['history']]
    assert any(e['check']=='Shipment route' and not e['passed'] for e in r['evidence'])
def test_investigation_and_role(auth):
    d=client.get('/api/data',headers=auth).json();id=d['investigations'][0]['id']
    assert client.post(f'/api/investigations/{id}/notes',headers=auth,json={'text':'Review documented evidence'}).status_code==200
    assert client.put(f'/api/investigations/{id}',headers=auth,json={'status':'Resolved'}).status_code==422
    u=client.get('/api/auth/me',headers=auth).json();u['role']='Pharmacist';restricted={'Authorization':'Bearer '+token(u)}
    assert client.post('/api/products',headers=restricted,json={'name':'Test','manufacturer':'Test'}).status_code==403
    assert client.post(f'/api/investigations/{id}/approval',headers=restricted,json={'action':'recall','decision':'approved','reason':'Documented review for testing'}).status_code==403
    assert client.post(f'/api/investigations/{id}/approval',headers=auth,json={'action':'quarantine','decision':'approved','reason':'Documented review for testing'}).status_code==200
def test_org_isolation(auth):
    other=client.post('/api/auth/demo').json();d=client.get('/api/data',headers=auth).json();id=d['products'][0]['id']
    assert client.get('/api/products/'+id,headers={'Authorization':'Bearer '+other['token']}).status_code==404
def test_exports_and_upload(auth):
    for f in ['csv','pdf']:
        r=client.post('/api/reports/generate',headers=auth,json={'kind':'verifications','format':f});assert r.status_code==200
        if f=='pdf':assert r.content.startswith(b'%PDF')
    d=client.get('/api/data',headers=auth).json();id=d['investigations'][0]['id']
    assert client.post(f'/api/investigations/{id}/evidence',headers=auth,files={'file':('test.txt',b'Test evidence','text/plain')}).status_code==200
    assert client.post(f'/api/investigations/{id}/evidence',headers=auth,files={'file':('x.html',b'<script>','text/html')}).status_code==415
