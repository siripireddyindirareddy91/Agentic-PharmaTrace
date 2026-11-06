# Architecture

Production: Browser → Vercel Services route table → Next.js for UI or FastAPI for `/api/*` → SQLAlchemy → ephemeral demo SQLite or configured PostgreSQL. FastAPI issues an HttpOnly SameSite=Lax cookie and checks identity, role, organization and mutation origins. Local development uses the same-origin Next.js proxy to reach the local FastAPI port. No service keys enter browser bundles.

LangGraph shares retrieved evidence across Orchestrator, Traceability, Batch Verification, Counterfeit Detection, Shipment Monitoring, Cold Chain Monitoring, Risk Assessment, Investigation, Compliance & Policy, and Report Generation. High-risk results conditionally route through Investigation; shipment tasks skip identity-specific agents. Each node records duration and success/failure. Incomplete workflows produce Unverified results requiring manual review.

Rule risk is the capped sum of explicit weights. Configurable demo bands: Low 0–29, Medium 30–59, High 60–79, Critical 80–100. A score is not a clinical probability. Unknown identifiers remain Unverified; duplication does not confirm counterfeit status. The optional OpenAI integration summarizes retrieved evidence and cannot approve actions. The synthetic classifier is experimental and does not silently replace rule evidence.

Audit and custody histories are append-only through application APIs. Database administrators can modify underlying storage. No blockchain or immutability claim is made.
