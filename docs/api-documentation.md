# API reference

Interactive OpenAPI documentation is available at backend `/docs`; machine-readable schema at `/openapi.json`. Data operations require a Bearer token, supplied by the Next.js HttpOnly cookie proxy.

| Group | Routes |
|---|---|
| Auth | POST /api/auth/demo, /register, /login; GET /api/auth/me |
| Workspace | GET /api/data |
| Products | GET/POST /api/products; GET/PUT /api/products/{id} |
| Batches | GET/POST /api/batches; GET /api/batches/{id}; POST /api/batches/{id}/serialize |
| Verification | POST /api/verification/verify; GET /api/verification/history, /api/verification/{id} |
| Signals | POST /api/counterfeit/analyze; GET /api/counterfeit/alerts; PUT /api/alerts/{id} |
| Traceability | GET /api/traceability/{serial}, /api/traceability/batch/{id} |
| Shipments | GET/POST /api/shipments; GET/PUT /api/shipments/{id}; POST /api/shipments/{id}/temperature |
| Agents | POST /api/agents/run; GET /api/agents, /api/agents/executions |
| Investigations | GET/POST /api/investigations; GET/PUT /api/investigations/{id}; POST /api/investigations/{id}/notes, /approval, /evidence |
| Analytics | GET /api/analytics/dashboard, /risk, /shipments |
| Reports | GET /api/reports; POST /api/reports/generate |
| Membership | GET /api/users; PUT /api/users/{id}/role |
| Experimental ML | POST /api/ml/predict |

Verification body: `{ "serial": "PT-2026-000003", "location": "Hyderabad" }`. Optional manufacturer and batch_number inputs trigger mismatch checks. PharmaTrace QR payloads use `PHARMATRACE:<serial>`. Results include status, rule risk, weighted evidence, workflow history and recommendation.

Report body: `{ "kind": "verifications", "format": "pdf", "search": "" }`; returns PDF or CSV. Evidence uses multipart `file`, accepting TXT/CSV/PDF up to 1 MB. HTTP errors use a detail field and appropriate 401/403/404/409/413/415/422/429 codes. Human approvals are documented decisions only; no physical regulated operation is executed.
