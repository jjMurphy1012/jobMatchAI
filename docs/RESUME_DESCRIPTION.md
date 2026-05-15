# Resume Project Description

## Recommended Resume Bullets

**JobMatchAI** | Personal Project | 2026

- Built a full-stack AI job matching platform with **FastAPI**, **React/TypeScript**, **PostgreSQL/pgvector**, and **Supabase Storage**, supporting resume upload, career profile extraction, admin-managed job sources, matches, tasks, and interview prep.
- Implemented production auth with **Google OAuth**, email registration/login, access/refresh cookie sessions, role-based access control, admin user management, and login rate limiting.
- Integrated **Greenhouse Job Board API** as a maintainable job source pipeline, with admin-configured company sources, sync run logs, opportunity upsert, closed-job marking, and source-level activation controls.
- Designed a matching pipeline using structured Career Profile fields, resume/opportunity embeddings, pgvector recall, and batched **GPT-4o-mini** reranking to improve match quality while controlling OpenAI cost.
- Moved cover letters to on-demand generation, reducing refresh latency and avoiding unnecessary LLM calls for matches the user never opens.
- Built an admin-curated Interview Prep workflow with review states, JSON import, company/role/topic/year filters, and related interview prep surfaced directly inside match details.
- Deployed with Docker on **Railway**, using Alembic migrations, Supabase Postgres pgvector, Supabase Storage, and GitHub-based continuous deployment.

## Condensed Version

**JobMatchAI** | Personal Project | 2026

- Built an AI job matching app with FastAPI, React/TypeScript, PostgreSQL/pgvector, Supabase Storage, Google OAuth, email auth, RBAC, resume management, career profile extraction, and admin workflows.
- Integrated Greenhouse job source sync with opportunity upsert/close handling, sync logs, embeddings, structured prefiltering, vector recall, and batched GPT reranking for cost-controlled matching.
- Added Interview Prep content workflow with admin review states, JSON import, filters, and related interview prep surfaced inside match details; deployed on Railway with Docker and Alembic.

## Interview Talking Points

### Matching Pipeline

The matching flow starts from user-owned data: the latest resume and effective Career Profile fields. Synced Greenhouse opportunities are filtered structurally by keywords, location, remote preference, internship intent, and excluded companies. Resume embeddings are used against opportunity embeddings with pgvector to recall semantically relevant jobs. A bounded top-N candidate set is then sent to GPT-4o-mini in batches for ranking, which reduces the number of LLM calls compared with scoring every opportunity individually.

### Why Greenhouse Sources

The project moved away from demo-style public scraping toward admin-managed company sources. Each source stores a Greenhouse board token and company name. Admins can sync a source, inspect fetched/upserted/closed counts, and disable stale sources. Jobs are persisted as shared `opportunities`, then users get personalized `user_job_matches`.

### Cost Control

The pipeline controls cost in three places:
- Structured prefilter before LLM ranking
- pgvector recall to prioritize semantically relevant jobs
- Batched LLM reranking with `MATCH_LLM_RERANK_LIMIT` and `MATCH_LLM_BATCH_SIZE`

Cover letters are generated only when the user clicks `Generate`, instead of being pre-generated for every match.

### Auth and Deployment

Auth uses cookie-based access and refresh tokens. The frontend retries failed authenticated requests by calling the refresh endpoint once. Google OAuth callback is routed through the frontend domain and proxied to the backend so cookies remain aligned with the browser-facing origin. Railway runs Alembic migrations before starting the backend, and Supabase provides Postgres, pgvector, and resume storage.

## Skills Highlighted

AI/ML:
- OpenAI embeddings
- GPT-4o-mini reranking
- LangChain / LangGraph
- Prompt design
- Vector recall with pgvector

Backend:
- FastAPI
- SQLAlchemy async
- Alembic
- PostgreSQL
- Cookie auth and RBAC
- External API integration

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS
- Responsive product UI

Infrastructure:
- Railway
- Supabase Postgres
- Supabase Storage
- Docker
- GitHub deploy flow

## ATS Keywords

```text
FastAPI, React, TypeScript, PostgreSQL, pgvector, Supabase, Railway, Docker,
Alembic, SQLAlchemy, OpenAI, GPT-4o-mini, Embeddings, Vector Search, RAG,
LangChain, LangGraph, OAuth, RBAC, Cookie Sessions, Greenhouse API,
Full Stack, AI Agent, Prompt Engineering, CI/CD
```
