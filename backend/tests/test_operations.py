from .test_workflows import client,auth
def test_import_and_excel(auth):
    r=client.post('/api/import/products',headers=auth,files={'file':('products.csv',b'name,manufacturer,min_temp,max_temp\nImported medicine,Aster Pharma,2,8','text/csv')})
    assert r.status_code==200,r.text
    assert r.json()['imported']==1
    bad=client.post('/api/import/products',headers=auth,files={'file':('bad.csv',b'name,manufacturer,min_temp,max_temp\nBad medicine,Aster Pharma,8,2','text/csv')})
    assert bad.status_code==422
    r=client.post('/api/reports/generate',headers=auth,json={'kind':'inventory','format':'xlsx'})
    assert r.status_code==200 and r.content.startswith(b'PK')
def test_transfer_idempotency_and_stock(auth):
    d=client.get('/api/data',headers=auth).json();stock=next(s for s in d['inventory'] if s['location']=='Hyderabad')
    body={'batch_id':stock['batch_id'],'origin':'Hyderabad','destination':'Test Warehouse','quantity':5,'reason':'Documented inventory transfer','idempotency_key':'test-transfer-001'}
    r=client.post('/api/inventory/transfer',headers=auth,json=body);assert r.status_code==200,r.text
    retry=client.post('/api/inventory/transfer',headers=auth,json=body);assert retry.json()['id']==r.json()['id']
    d=client.get('/api/data',headers=auth).json();assert next(s for s in d['inventory'] if s['id']==stock['id'])['quantity']==stock['quantity']-5
    body.update(quantity=1000000,idempotency_key='test-transfer-002');assert client.post('/api/inventory/transfer',headers=auth,json=body).status_code==409
