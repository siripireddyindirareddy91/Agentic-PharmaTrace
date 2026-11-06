# Validation record

- Backend integration suite: 10 passing tests, covering protected APIs, seed volumes, registration/batch validation, serialization, QR parsing, unknown identifiers, duplicate location checks, expiry, cold-chain excursions, route anomalies, LangGraph task routing, role restrictions, organization isolation, investigation notes and human approvals, PDF/CSV export and evidence file validation.
- TypeScript: passed `tsc --noEmit`.
- Local production build: passed Next.js webpack build. The local Windows Turbopack child-process issue does not occur in the Vercel Linux build; hosted Turbopack build passed.
- Deployed API smoke test: demo login 200, cookie-authenticated `/api/data` 200 with 15 products / 25 batches / 100 serialized units / 20 shipments, verification 200, PDF export 200 with PDF signature.
- Experimental model: 3,750 synthetic training records and 1,250 held-out synthetic evaluation records. Precision 0.812, recall 0.868, F1 0.839, ROC-AUC 0.947. See `ml-models/artifacts/metrics.json`. These metrics establish no real-world counterfeit accuracy.

Known operational limits and unimplemented production requirements are listed in README. No Supabase project credentials or new Vercel credential secrets were configured, per user preference. GitHub source is pushed; automatic Vercel Git integration remains unlinked because the connector lacks repository access.
