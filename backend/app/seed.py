from .database import *
from datetime import date, timedelta

DRUGS = ['Paracetamol 500 mg','Amoxicillin 250 mg','Insulin Glargine','Metformin 500 mg','Atorvastatin 20 mg','Amlodipine 5 mg','Ceftriaxone 1 g','Pantoprazole 40 mg','Human Albumin 20%','Doxycycline 100 mg','Salbutamol Inhaler','Levothyroxine 50 mcg','Hepatitis B Vaccine','Azithromycin 500 mg','Losartan 50 mg']
CITIES = ['Hyderabad','Bengaluru','Mumbai','Chennai','Pune','Delhi','Ahmedabad','Kolkata','Kochi','Jaipur']
def seed(db, org='demo'):
    if db.query(Record).filter_by(org=org, kind='products').first(): return
    for i, city in enumerate(CITIES):
        add(db,'organizations',{'name':['Aster Pharma','Nova Biologics','MedAxis Distribution','CareLink Logistics','Apollo Pharmacy','City General Hospital','Zenith Labs','Metro Warehouse','HealthFirst Pharmacy','Unity Hospital'][i], 'type':['Manufacturer','Manufacturer','Distributor','Distributor','Pharmacy','Hospital','Manufacturer','Warehouse','Pharmacy','Hospital'][i], 'location':city,'status':'Registered','contact':f'operations{i+1}@example.test'},org,f'{org}-org-{i}')
    for i,name in enumerate(DRUGS):
        add(db,'products',{'name':name,'manufacturer':'Aster Pharma' if i%2==0 else 'Nova Biologics','category':'Biologic' if i in [2,8,12] else 'General medicine','min_temp':2 if i in [2,8,12] else 15,'max_temp':8 if i in [2,8,12] else 30,'barcode':f'0890123400{i:03}','status':'Registered'},org,f'{org}-product-{i}')
    for i in range(25):
        add(db,'batches',{'batch_number':f'BT-2026-{i+1:04}','product_id':f'{org}-product-{i%15}','product':DRUGS[i%15],'manufacturer':'Aster Pharma' if i%15%2==0 else 'Nova Biologics','manufactured':str(date.today()-timedelta(days=180)),'expiry':str(date.today()+timedelta(days=-10 if i==4 else 365+i*3)),'quantity':1200+i*50,'status':'Quarantined' if i==7 else 'Active','quality':'Passed','min_temp':2 if i%15 in [2,8,12] else 15,'max_temp':8 if i%15 in [2,8,12] else 30},org,f'{org}-batch-{i}')
    for i in range(100):
        b=i%25
        add(db,'serials',{'serial':f'PT-2026-{i+1:06}','batch_id':f'{org}-batch-{b}','product_id':f'{org}-product-{b%15}','product':DRUGS[b%15],'status':'Unverified'},org,f'{org}-serial-{i}')
        for j,stage in enumerate(['Manufactured','Quality inspected','Serialized','Dispatched','Received']):
            if i==7 and j in [1,4]: continue
            add(db,'events',{'serial':f'PT-2026-{i+1:06}','batch_id':f'{org}-batch-{b}','stage':stage,'organization':'Aster Pharma' if j<3 else 'MedAxis Distribution','location':CITIES[(i+j)%10],'timestamp':(datetime.now(timezone.utc)-timedelta(days=20-j*3)).isoformat(),'responsible_user':'Synthetic operations','status':'Recorded'},org)
    for i in range(20):
        b=i%25
        add(db,'shipments',{'reference':f'SHP-{i+1:04}','batch_id':f'{org}-batch-{b}','product':DRUGS[b%15],'origin':CITIES[i%10],'destination':CITIES[(i+3)%10],'location':CITIES[(i+1)%10],'status':['In transit','Delivered','Delayed','Dispatched'][i%4],'quantity':100+i*10,'route_deviation':i in [7,12],'expected_delivery':str(date.today()+timedelta(days=-2 if i%4==2 else 2)),'min_temp':2 if b%15 in [2,8,12] else 15,'max_temp':8 if b%15 in [2,8,12] else 30},org,f'{org}-shipment-{i}')
        for j in range(12):
            cold=b%15 in [2,8,12]
            add(db,'temperatures',{'shipment_id':f'{org}-shipment-{i}','temperature':round((4.5 if cold else 23)+(j%4-2)*.6+(8 if i==2 and j>7 else 0),1),'timestamp':(datetime.now(timezone.utc)-timedelta(hours=12-j)).isoformat()},org)
        add(db,'inventory',{'product':DRUGS[b%15],'batch_id':f'{org}-batch-{b}','location':CITIES[i%10],'quantity':100+i*10,'status':'Quarantined' if i==7 else 'Available'},org)
    for i in range(30):
        add(db,'verifications',{'serial':f'PT-2026-{i+1:06}','product':DRUGS[(i%25)%15],'status':'Suspicious' if i%7==0 else 'Verified','risk':65 if i%7==0 else 5,'location':CITIES[i%10],'evidence':[],'mode':'Synthetic seed'},org)
    for i,(title,cat) in enumerate([('Temperature excursion on insulin shipment','Cold chain'),('Unexpected route change detected','Shipment'),('Incomplete custody records','Traceability'),('Expired batch requires review','Expiry')]):
        add(db,'alerts',{'title':title,'category':cat,'priority':['Critical','High','Medium','High'][i],'status':'Open','serial':f'PT-2026-{i+3:06}'},org)
    add(db,'investigations',{'title':'Review insulin temperature excursion','serial':'PT-2026-000003','risk':70,'status':'New','assigned_to':'Unassigned','notes':[],'approvals':[],'evidence':[],'recommendation':'Inspect shipment and request authorized review.'},org)
    add(db,'policies',{'name':'Product-specific storage policy','description':'Compare each reading to the registered product limits. Excursions require documented human review; do not automatically release or recall stock.'},org)
    db.commit()
