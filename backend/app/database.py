import os, uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, JSON, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc).isoformat()
url = os.getenv('DATABASE_URL', 'sqlite:////tmp/pharmatrace.db' if os.getenv('VERCEL') else 'sqlite:///./pharmatrace.db')
if url.startswith('postgres://'): url = url.replace('postgres://', 'postgresql+psycopg://', 1)
if url.startswith('postgresql://'): url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
engine = create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {}, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
class Record(Base):
    __tablename__ = 'records'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String, index=True)
    org: Mapped[str] = mapped_column(String, index=True, default='demo')
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String, default=now)
class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default='Pharmacist')
    org: Mapped[str] = mapped_column(String, default='demo')

def records(db, kind, org='demo'):
    return [dict(r.data, id=r.id, created_at=r.created_at) for r in db.query(Record).filter_by(kind=kind, org=org).order_by(Record.created_at.desc()).all()]
def add(db, kind, data, org='demo', id=None):
    r = Record(id=id or uid(), kind=kind, data=data, org=org); db.add(r); db.flush(); return dict(data, id=r.id, created_at=r.created_at)
def audit(db, actor, action, entity, detail=''):
    add(db, 'audit', {'actor':actor['email'], 'action':action, 'entity':entity, 'detail':detail}, actor['org'])
