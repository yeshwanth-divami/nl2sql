# BRD

## Executive Summary

NL2SQL enables business and technical users to ask questions in natural language and receive safe, reviewable SQL with tabular answers over existing databases. The business problem is slow, error‑prone translation from questions to correct SQL, which delays decisions and increases analyst workload. This initiative will deliver a read‑only, governance‑aware capability focused on PostgreSQL and DuckDB first, accessible via a simple Python interface and lightweight reporting (tables, brief summaries, basic charts, and exports). Value at stake includes reduced time‑to‑insight, higher analyst throughput, and safer ad‑hoc querying. Scope emphasizes schema‑grounded NL→SQL, execution with guardrails, auditing, and observability; full BI dashboards, ETL, and write operations are explicitly out of scope.

## Problem & Context

The current process for turning business questions into SQL is slow, inconsistent, and risky for non‑experts. Schema complexity, drift, and permission boundaries increase errors and rework, while modern teams need faster, safer self‑serve access to data across existing databases.

- Market: Rising demand for self‑serve analytics without replacing existing data platforms
- Regulatory/compliance: Need for read‑only defaults, auditability, and governance alignment
- Customer pain: Delays in ad‑hoc insights; ambiguity and SQL errors for non‑experts
- Operational drivers: Reduce analyst tickets/hand‑offs; standardize guardrails and traceability

## Objectives (SMART)
ID | Objective (Specific) | Target Metric(s) (Measurable) | Target Date (Time‑bound)
---|---|---|---
OBJ‑001 | Ship MVP: Read‑only NL→SQL for PostgreSQL and DuckDB with schema introspection, execution, tabular results, and exports for an internal pilot | Pilot weekly active users ≥5 | 2025‑10‑31
OBJ‑002 | Safety & Accuracy | DML/DDL prevention ≥95%; schema reference error rate ≤2% | 2025‑12‑31
OBJ‑003 | Performance | NL→result latency ≤6s (P50) and ≤12s (P95) on typical ad‑hoc queries (≤10M rows) | 2025‑12‑31
OBJ‑004 | Governance & Audit | 100% of executed queries logged; approvals enforced for flagged/risky queries | 2025‑11‑30
OBJ‑005 | Developer Adoption | SDK + docs with 3 reference examples; ≥3 internal integrations | 2025‑11‑15; 2025‑12‑31

## Scope
**In**
- NL→SQL grounded on live schema for PostgreSQL and DuckDB (read‑only)
- Schema discovery/introspection and refresh
- SQL execution with tabular results and brief NL summary
- Lightweight charts (bar/line) and exports (CSV/JSON/Markdown)
- Python API/SDK for simple embedding and invocation
- Guardrails: permission checks, DML/DDL prevention, risky‑query flags
- Audit logging and basic observability/tracing hooks

**Out**
- Any DML/DDL (writes/mutations), role escalation, or schema changes
- Full BI/dashboard designer, complex visualization suite
- ETL/ELT, data modeling, or warehouse orchestration
- PII re‑classification; relies on upstream data governance and DB permissions
- Non‑PostgreSQL or non‑DuckDB engines in MVP (future consideration)

## Stakeholders & RACI (overview)
Role | Name | R | A | C | I
---|---|---|---|---|---
Business Owner | TBD |  | A |  | I
Product Owner | TBD | R |  | C | I
Technology Owner | TBD | R |  | C | I
Data Governance | TBD |  |  | C | I
Security | TBD |  |  | C | I
SRE/Platform | TBD |  |  | C | I
Documentation Lead | TBD |  |  | C | I

## Requirements Summary
ID | Requirement | Type | Priority | Rationale
---|---|---|---|---
BRD‑F‑001 | Convert NL to SQL grounded on live schema for PostgreSQL and DuckDB | Functional | Must | Ties to OBJ‑001
BRD‑F‑002 | Enforce read‑only guardrail; block/strip DML/DDL | Functional | Must | Ties to OBJ‑002
BRD‑F‑003 | Schema introspection and on‑demand refresh | Functional | Must | Ties to OBJ‑001, OBJ‑002
BRD‑F‑004 | Execute SQL and return tabular results | Functional | Must | Ties to OBJ‑001
BRD‑F‑005 | Generate concise NL summary of results | Functional | Should | Ties to OBJ‑001
BRD‑F‑006 | Export results as CSV/JSON/Markdown | Functional | Should | Ties to OBJ‑001
BRD‑F‑007 | Basic charts (bar/line) rendering | Functional | Could | Ties to OBJ‑001
BRD‑F‑008 | Python API/SDK to supply connection and invoke agent | Functional | Must | Ties to OBJ‑005
BRD‑F‑009 | Audit log with user, SQL, datasource, timing, and outcome | Functional | Must | Ties to OBJ‑004
BRD‑F‑010 | Admin controls for approvals/risky‑query gating | Functional | Should | Ties to OBJ‑004
BRD‑NF‑001 | Latency: ≤6s P50 and ≤12s P95 NL→result | Non‑Functional | Must | Ties to OBJ‑003
BRD‑NF‑002 | Safety & Accuracy: ≥95% DML/DDL prevention; ≤2% schema errors | Non‑Functional | Must | Ties to OBJ‑002
BRD‑NF‑003 | Security: read‑only execution, no privilege escalation, least‑privileged access | Non‑Functional | Must | Ties to OBJ‑004
BRD‑NF‑004 | Observability: tracing hooks and query outcome metrics | Non‑Functional | Should | Ties to OBJ‑004
BRD‑NF‑005 | Cost control: configurable model/provider and per‑query caps | Non‑Functional | Could | Ties to OBJ‑003

## Assumptions & Constraints
Assumptions
- Owners and named resources are placeholders pending assignment
- Initial engines: PostgreSQL (12+) and DuckDB; additional engines to be evaluated later
- Pilot datasets will be non‑sensitive or governed datasets suitable for read‑only access
- SDK delivered in Python; service‑hosting is optional and outside MVP scope

Constraints
- Timeline: MVP by 2025‑Q4; GA decisions post‑pilot
- Budget: Pilot‑scale LLM usage; prefer cost caps and caching; small team (2–3 FTE in Q4)
- Technology: Python 3.10+; Postgres 12+; DuckDB current stable
- Compliance: Read‑only enforcement; auditability; align with existing data governance
- Data governance: No storage of raw query results beyond execution; respect DB‑level PII controls

## Risks & Dependencies
ID | Risk/Dependency | Impact | Likelihood | Mitigation/Owner
---|---|---|---|---
RISK‑001 | Hallucinated SQL or schema mismatch | High | Medium | Strong schema grounding, validation, tests; Owner: Tech
RISK‑002 | Latency on large/complex queries | High | Medium | Pagination, limits, sampling, async planning; Owner: Tech/SRE
RISK‑003 | Security/compliance gaps | High | Low‑Med | Read‑only, approvals, audits, pen‑test; Owner: Security
RISK‑004 | LLM/provider dependency and cost | Med | Med | Pluggable providers, caching, evals; Owner: Product/Tech
RISK‑005 | Low adoption by analysts | Med | Med | Clear docs, templates, enablement; Owner: Product
DEP‑001 | Access to governed Postgres/DuckDB datasources | High | Med | Early environment setup; Owner: Tech

## Milestones & Timeline
ID | Milestone | DoD | Target Date | Owner | Deps
---|---|---|---|---|---
MS‑001 | MVP NL→SQL (PG/DuckDB) | NL→SQL, schema introspect, execute, table + exports | 2025‑10‑31 | Tech | DEP‑001
MS‑002 | Safety hardening | DML/DDL prevention, risky‑query flags | 2025‑11‑15 | Tech/Security | MS‑001
MS‑003 | Audit & approvals | Query log + approval workflow | 2025‑11‑30 | Tech | MS‑001
MS‑004 | SDK & docs | Python package + 3 reference examples | 2025‑11‑15 | Docs/Product | MS‑001
MS‑005 | Latency tuning | Meet P50/P95 latency targets | 2025‑12‑15 | SRE/Tech | MS‑001
MS‑006 | Pilot sign‑off | Objectives met; stakeholder approval | 2025‑12‑31 | Business | MS‑001–MS‑005

## Success Criteria & Acceptance Metrics
Objective | Metric | Baseline | Target | Window | Source | Cadence
---|---|---|---|---|---|---
OBJ‑001 | Weekly active pilot users | 0 | ≥5 | Pilot | Usage logs | Weekly
OBJ‑001 | Pilot queries executed/week | 0 | ≥50 | Pilot | Audit logs | Weekly
OBJ‑002 | DML/DDL blocked rate | N/A | ≥95% | Pilot | Audit logs | Bi‑weekly
OBJ‑002 | Schema reference error rate | Unknown | ≤2% | Pilot | Eval set | Bi‑weekly
OBJ‑003 | NL→result latency (P50/P95) | Unknown | ≤6s / ≤12s | Pilot | Traces | Weekly
OBJ‑004 | Queries with complete audit entries | Unknown | 100% | Pilot | Audit logs | Weekly
OBJ‑005 | Reference integrations completed | 0 | ≥3 | Pilot | Repo/docs | By 2025‑12‑31

Traceability Map: OBJ‑001 ↔ BRD‑F‑001/003/004/006/008 ↔ MS‑001/MS‑004 ↔ Usage, Queries/week; OBJ‑002 ↔ BRD‑F‑002/‑NF‑002 ↔ MS‑002/MS‑003 ↔ Block rate, Error rate; OBJ‑003 ↔ BRD‑NF‑001 ↔ MS‑005 ↔ Latency P50/P95; OBJ‑004 ↔ BRD‑F‑009/010/‑NF‑003/004 ↔ MS‑002/MS‑003 ↔ 100% audit; OBJ‑005 ↔ BRD‑F‑008 ↔ MS‑004 ↔ Integrations.

## Cost–Benefit Snapshot
- CapEx/Build: 2–3 FTE for Q4 2025; minimal infra beyond development environments
- OpEx (pilot): LLM usage and hosting costs on the order of $1k–$3k/month depending on volume and provider
- Benefits: 30–50% reduction in ad‑hoc analyst tickets, faster time‑to‑insight for business users, standardized guardrails and auditability
- Payback/ROI: Expected within 1–2 quarters post‑pilot if adopted by ≥3 internal teams; assumes 50+ queries/week and reduced analyst time per request

## Glossary (Key Terms & Data Entities)
- NL2SQL — Natural Language to SQL conversion
- Safe Mode — Read‑only execution with DML/DDL prevention
- Schema Introspection — Automated retrieval of tables/columns/relationships
- Guardrails — Policies to enforce safety and governance
- Report — Table of results plus brief NL summary and optional simple chart

## Open Questions / Decisions Needed
- Confirm Business, Product, and Technology owners; assign names and availability (Owner: Business, Due: 2025‑09‑15)
- Approve pilot datasources and access scopes (Owner: Data Governance, Due: 2025‑09‑30)
- Select default LLM provider(s) and cost caps (Owner: Tech/Product, Due: 2025‑09‑30)
- Define risky‑query criteria and approval policy (Owner: Security, Due: 2025‑10‑15)
- Decide engines beyond PG/DuckDB for post‑pilot roadmap (Owner: Product, Due: 2025‑11‑30)

## Feature Requirements Index (FRDs to author next)
FRD ID | Title | Brief Outcome | Primary Owner | Stakeholders | Notes
---|---|---|---|---|---
FRD‑001 | Authentication & Access Control | Enforce read‑only, roles, approvals | Tech/Security | Product, Governance | MVP scope is minimal
FRD‑002 | Schema Discovery & Connectors (PG/DuckDB) | Introspect schema; refresh; connectors | Tech | Product, Governance | Core grounding
FRD‑003 | NL→SQL Planning & Generation | Plan and generate grounded SQL | Tech | Product | Deterministic prompts, evals
FRD‑004 | Query Execution & Results | Execute safely; return tables | Tech | Security | Timeouts/limits
FRD‑005 | Reporting (Summaries, Charts, Exports) | NL summary, basic charts, CSV/JSON/MD | Product | Tech | Lightweight only
FRD‑006 | Audit, Logging & Approvals | Full audit trail and approval workflow | Security | Tech, Governance | Compliance alignment
FRD‑007 | Python SDK & Integration Guides | Simple API; 3 reference examples | Tech | Docs, Product | Packaging/versioning
FRD‑008 | Observability & Cost Controls | Tracing hooks; latency/cost metrics | SRE/Tech | Product | Budgets/alerts
FRD‑009 | Caching & Templates | Reuse prompt/plans; reduce latency/cost | Tech | Product | Optional in MVP
FRD‑010 | Admin Console (Minimal) | Configs, approvals, logs | Product | Tech, Security | Scope MVP‑light
FRD‑011 | Data Governance & Retention | Policies for logs/exports | Governance | Security, Tech | Read‑only posture
FRD‑012 | Security Hardening & Pen‑Test | Threat model, pen‑test fixes | Security | Tech | Pre‑sign‑off
FRD‑013 | Billing & Plans (If externalized) | Usage accounting, quotas | Product | Finance, Tech | Post‑pilot
FRD‑014 | SLA & SRE Readiness | Targets, runbooks, alerts | SRE | Tech, Product | Post‑MVP scale

