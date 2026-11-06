# Database design

The runtime uses SQLAlchemy `users` and `records` tables. Records are indexed by organization and kind. Every repository read and write is scoped by organization. JSON evidence preserves agent results and historical snapshots. SQLite persists locally; PostgreSQL is supported through DATABASE_URL. Direct browser access to database tables is not enabled.

The normalized PostgreSQL reference schema expresses the target enterprise model with foreign keys, unique serialization constraints, indexed relations and RLS policies. It is separate from the executable JSON repository: applying it does not migrate or switch the running application. This is an explicit remaining production task.

`backend/app/seed.py` is the executable synthetic seed implementation. The same data is created for isolated demo sessions. It is not an official pharmaceutical registry.
