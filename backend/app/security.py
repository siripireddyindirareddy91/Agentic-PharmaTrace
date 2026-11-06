import os, hashlib, secrets, hmac, time
import jwt, httpx
from fastapi import HTTPException, Request, Depends
from .database import Session, User

SECRET=os.getenv('JWT_SECRET') or secrets.token_hex(32)
DEMO=os.getenv('DEMO_MODE','true').lower()=='true'
def password_hash(password, salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),310000).hex()
def password_check(password, stored): return hmac.compare_digest(password_hash(password,stored.split(':')[0]), stored)
def token(user): return jwt.encode(dict(user, exp=int(time.time())+28800),SECRET,algorithm='HS256')
def get_db():
    with Session() as db:
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
def current(request:Request, db=Depends(get_db)):
    raw=request.headers.get('authorization','').removeprefix('Bearer ')
    if not raw: raise HTTPException(401,'Sign in required')
    try:
        payload=jwt.decode(raw,SECRET,algorithms=['HS256'])
        if payload.get('email')!='demo@example.test':
            stored=db.query(User).filter_by(id=payload.get('id')).first()
            if not stored: raise HTTPException(401,'Account no longer exists')
            payload.update(role=stored.role,org=stored.org)
        return payload
    except jwt.InvalidTokenError:
        if os.getenv('SUPABASE_URL'):
            try:
                response=httpx.get(os.environ['SUPABASE_URL']+'/auth/v1/user',headers={'apikey':os.environ['SUPABASE_ANON_KEY'],'Authorization':'Bearer '+raw},timeout=10)
                response.raise_for_status(); data=response.json()
                user=db.query(User).filter_by(email=data['email']).first()
                if user: return {'id':user.id,'email':user.email,'name':user.name,'role':user.role,'org':user.org}
            except Exception: pass
        raise HTTPException(401,'Session expired. Please sign in again.')
def allowed(user, roles):
    if user['role']!='System Administrator' and user['role'] not in roles: raise HTTPException(403,'Your role does not permit this action')
