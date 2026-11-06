# Executable synthetic seed

The seed implementation is `backend/app/seed.py`, automatically called for each isolated demonstration organization. To seed a local database manually, run from repository root:

```powershell
python -c "from backend.app.database import Base,engine,Session; from backend.app.seed import seed; Base.metadata.create_all(engine); db=Session(); seed(db); db.close()"
```

The normalized schema is a separate design reference and needs an explicit repository/data migration before use.
