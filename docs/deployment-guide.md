# Deployment guide

## Current unified deployment

The root vercel.json uses Vercel Services (beta): Next.js and FastAPI build separately and deploy atomically in `pharmatrace-ai`. Same-origin `/api/*` requests go directly to the authenticated FastAPI service, while all UI routes go to Next.js. FastAPI uses an HttpOnly SameSite=Lax session cookie and checks cross-origin mutations. No backend protection-bypass credential is created. Deploy from the repository root with no rootDirectory override. The project-level framework should remain unset; frameworks are set per service. Local development retains the Next.js API proxy.

The user requested deployment without adding credentials. JWT_SECRET is therefore generated per backend process. Sessions can expire on instance recycling, and SQLite demo data is ephemeral. Do not use this deployment to retain real records. Vercel's existing deployment protection is preserved. A separate API project was also deployed during setup; the unified app uses its own private backend instead.

GitHub source is pushed, but the Vercel connector's GitHub integration did not have repository-link access. Deployment used the tracked source-file catalog. Automatic deploy-on-push is not configured; connect the repository in Vercel when its GitHub integration has access.

## Frontend on Vercel

Import the GitHub repository with root `frontend`, framework Next.js and build `npm run build`. Set server-only API_URL to the backend HTTPS origin without `/api`. No secrets may use NEXT_PUBLIC_ prefixes.

## FastAPI on Vercel

Import the repository with root `backend` and framework Other. `api/index.py` exposes the ASGI app. Set a stable cryptographically random JWT_SECRET, DEMO_MODE=true and ALLOWED_ORIGINS to the frontend origin. Supply DATABASE_URL for persistence. Without it the hosted demo explicitly uses ephemeral `/tmp` SQLite and must not retain real pharmaceutical records.

## Render alternative

Use render.yaml, or build `pip install -r requirements.txt` and start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Health check `/health`; API documentation `/docs`. Use durable PostgreSQL rather than an ephemeral disk.

## Supabase setup

Create a project and use its PostgreSQL pooler URL as DATABASE_URL with dialect `postgresql+psycopg://`. Runtime tables are initialized by SQLAlchemy. Set SUPABASE_URL and SUPABASE_ANON_KEY for optional Auth integration. Provision organization memberships under administrator control. Disable DEMO_MODE for real data. Use a least-privileged server database role and reviewed RLS policies. The normalized reference schema is separate from the current runtime repository and requires an explicit migration.

## Troubleshooting

- API 503: inspect API_URL, backend `/health`, runtime logs and deployment protection.
- 401 after restart: set a stable JWT_SECRET. After ephemeral database recycling, start a fresh demo session.
- 403: the authenticated role is not authorized. Registration deliberately grants Pharmacist rights.
- Camera unavailable: use serial input; camera requires HTTPS and BarcodeDetector support.
- Windows Turbopack worker failure: use the documented webpack build.

Before real-world use, configure durable PostgreSQL, verified Supabase authentication, shared rate limits, durable file storage, organization invitations, monitoring, backup/restore and security review. Complete the relational repository migration and stock reconciliation. This demo has no regulatory validation.
