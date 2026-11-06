# Architecture

Browser → Next.js App Router → same-origin API proxy → FastAPI → SQLAlchemy → SQLite locally or PostgreSQL through DATABASE_URL. The proxy keeps the bearer token in an HttpOnly SameSite=Lax cookie. Backend checks identity, role and organization. No service keys enter browser bundles.

LangGraph shares retrieved evidence across Orchestrator, Traceability, Batch Verification, Counterfeit Detection, Shipment Monitoring, Cold Chain Monitoring, Risk Assessment, Investigation, Compliance & Policy, and Report Generation. High-risk results conditionally route through Investigation; shipment tasks skip identity-specific agents. Each node records duration and success/failure. Incomplete workflows produce Unverified results requiring manual review.

Rule risk is the capped sum of explicit weights. Configurable demo bands: Low 0–29, Medium 30–59, High 60–79, Critical 80–100. A score is not a clinical probability. Unknown identifiers remain Unverified; duplication does not confirm counterfeit status. The optional OpenAI integration summarizes retrieved evidence and cannot approve actions. The synthetic classifier is experimental and does not silently replace rule evidence.

Audit and custody histories are append-only through application APIs. Database administrators can modify underlying storage. No blockchain or immutability claim is made.
