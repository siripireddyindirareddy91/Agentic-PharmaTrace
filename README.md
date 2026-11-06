# PharmaTrace AI

Pharmaceutical supply-chain traceability and risk investigation using Next.js, FastAPI, SQLAlchemy and LangGraph. Supplied records are synthetic. Results are not laboratory confirmations, regulatory certifications or authorizations to recall, release or destroy medicine.

## Run locally

Requires Node.js 22+ and Python 3.12.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:JWT_SECRET = 'your-random-secret-at-least-32-characters'
python -m uvicorn backend.app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000 and select **Open synthetic demo**. Each demo session has an isolated organization with 15 products, 25 batches, 100 serialized units, 20 shipments, 498 custody events, 240 temperature readings and 30 verification records. Registration grants Pharmacist permissions. Demo administrator permissions affect only synthetic session data.

## Features

- Database-driven dashboard; searchable tables, filters, pagination and responsive navigation.
- Products, batches, serialization, downloadable QR images and browser camera scanning where supported.
- Evidence-based verification: identifier registry, expiry, batch/manufacturer mismatch, rapid checks from different locations, custody gaps, shipment delays, route deviations and product-specific storage temperatures.
- Ten coordinated LangGraph specialist nodes, shared state, conditional routing, execution history and optional OpenAI evidence summaries.
- Custody timelines, shipment milestones, temperature entry, inventory movement journals, investigations, notes, evidence uploads and documented human approvals.
- Backend role and organization checks, HttpOnly same-site session cookies, PBKDF2 demo passwords, validation and per-process rate limits.
- PDF/CSV exports, alert acknowledgement/resolution and append-only application audit entries.
- Optional synthetic scikit-learn classifier with held-out evaluation; explainable rules remain independent.

## Validation

```powershell
python -m pytest backend/tests -v
cd frontend
npm run typecheck
npm run build
```

Windows Turbopack fallback: `node node_modules/next/dist/bin/next build --webpack`.

Optional model training: `pip install -r backend/requirements-ml.txt`, then `python ml-models/training/train.py`.

## Deployment

Vercel frontend root: `frontend`, server-only API_URL points to backend origin. Vercel FastAPI root: `backend`. A Render blueprint is supplied. See [deployment guide](docs/deployment-guide.md), [architecture](docs/architecture.md), [API reference](docs/api-documentation.md), and [database design](docs/database-design.md). Copy configuration names from `.env.example`; never commit secrets.

## Updated operations

CSV/XLSX product imports validate the complete file before writing (500 rows / 1 MB), reject formulas and oversized expanded workbooks, and record an audit entry. Excel exports neutralize formula injection. Inventory transfers atomically debit and credit available stock with a journal, PostgreSQL row locks, expiry/quarantine checks and idempotency keys. GitHub Actions runs backend tests and frontend builds on pushes and pull requests. Production mode now refuses to start without PostgreSQL and a stable signing secret.

## Current boundaries

The hosted no-credential demo uses serverless `/tmp` SQLite: records can reset on instance recycling and are not shared across instances. Configure PostgreSQL and a stable JWT_SECRET for durable operation. Runtime uses an organization-scoped JSON repository and relational users table. The normalized PostgreSQL reference schema requires a repository migration before adoption. Supabase Auth requires project credentials and configured memberships. Supabase Storage is not connected; evidence is kept in the database with a 1 MB upload limit. Imports currently cover product registries. Maps use interactive route diagrams. Inventory transfers reconcile stock, while shipment dispatch/receipt reconciliation remains a separate workflow. Rate limits are process-local. Automatic Vercel deployments require enabling repository access in the Vercel GitHub integration. No automatic regulated action occurs, and real-world counterfeit accuracy has not been validated. These account and architecture requirements prevent a production-ready claim.
