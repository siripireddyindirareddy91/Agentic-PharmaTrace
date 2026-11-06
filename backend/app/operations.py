import csv,io,zipfile
from fastapi import Depends,HTTPException,UploadFile,File
from pydantic import BaseModel,Field,ValidationError
from .database import Record,records,add,audit,uid
from .security import current,get_db,allowed

def install(app,ProductInput):
    @app.post('/api/import/products')
    async def import_products(file:UploadFile=File(...),user=Depends(current),db=Depends(get_db)):
        allowed(user,['Manufacturer'])
        content=await file.read(1048577)
        if len(content)>1048576:raise HTTPException(413,'Maximum import size is 1 MB')
        try:
            if (file.filename or '').lower().endswith('.csv'):
                rows=list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))))
            elif (file.filename or '').lower().endswith('.xlsx'):
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    if sum(x.file_size for x in archive.infolist())>10000000:raise ValueError('Expanded workbook exceeds 10 MB')
                from openpyxl import load_workbook
                book=load_workbook(io.BytesIO(content),read_only=True,data_only=False);values=book.active.iter_rows(values_only=True);headers=next(values);rows=[dict(zip(headers,row)) for row in values];book.close()
            else:raise HTTPException(415,'Upload CSV or XLSX')
            if not rows or len(rows)>500:raise ValueError('Import must contain between 1 and 500 product rows')
            validated=[]
            for index,row in enumerate(rows,2):
                cleaned={k:v for k,v in row.items() if k and v is not None and v!=''}
                if any(isinstance(v,str) and v.startswith('=') for v in cleaned.values()):raise ValueError(f'Row {index}: formulas are not allowed')
                p=ProductInput.model_validate(cleaned)
                if p.min_temp>=p.max_temp:raise ValueError(f'Row {index}: invalid temperature limits')
                validated.append(p.model_dump())
        except HTTPException:raise
        except (ValueError,KeyError,StopIteration,zipfile.BadZipFile,ValidationError) as exc:raise HTTPException(422,str(exc)[:500])
        result=[add(db,'products',dict(p,status='Registered'),user['org']) for p in validated]
        audit(db,user,'Import products',str(len(result)),file.filename or '')
        return {'imported':len(result),'records':result}

    class Movement(BaseModel):
        batch_id:str
        origin:str=Field(min_length=2,max_length=100)
        destination:str=Field(min_length=2,max_length=100)
        quantity:int=Field(gt=0,le=1000000)
        reason:str=Field(min_length=10,max_length=1000)
        idempotency_key:str=Field(min_length=8,max_length=100)
    @app.post('/api/inventory/transfer')
    def transfer(body:Movement,user=Depends(current),db=Depends(get_db)):
        allowed(user,['Warehouse Manager','Distributor'])
        if body.origin==body.destination:raise HTTPException(422,'Choose different origin and destination')
        lock=db.query(Record).filter_by(org=user['org'],kind='batches',id=body.batch_id).with_for_update().first()
        if not lock:raise HTTPException(404,'Batch not found')
        if lock.data.get('status')!='Active':raise HTTPException(409,'Batch is not available for transfer')
        if lock.data.get('expiry','')<__import__('datetime').date.today().isoformat():raise HTTPException(409,'Expired stock cannot be transferred')
        existing=next((x for x in records(db,'inventory_transactions',user['org']) if x.get('idempotency_key')==body.idempotency_key),None)
        if existing:return existing
        stocks=db.query(Record).filter_by(org=user['org'],kind='inventory').with_for_update().all()
        source=next((x for x in stocks if x.data.get('batch_id')==body.batch_id and x.data.get('location')==body.origin and x.data.get('status')=='Available'),None)
        if not source or source.data['quantity']<body.quantity:raise HTTPException(409,'Insufficient available stock')
        dest=next((x for x in stocks if x.data.get('batch_id')==body.batch_id and x.data.get('location')==body.destination and x.data.get('status')=='Available'),None)
        source.data=dict(source.data,quantity=source.data['quantity']-body.quantity)
        if dest:dest.data=dict(dest.data,quantity=dest.data['quantity']+body.quantity)
        else:add(db,'inventory',{'batch_id':body.batch_id,'product':lock.data['product'],'location':body.destination,'quantity':body.quantity,'status':'Available'},user['org'])
        transaction=add(db,'inventory_transactions',dict(body.model_dump(),type='Transfer',actor=user['email']),user['org']);audit(db,user,'Transfer inventory',transaction['id'],body.reason);return transaction
