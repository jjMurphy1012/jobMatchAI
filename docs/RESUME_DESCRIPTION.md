# Resume Project Description

## For Resume Use

### Option 1: Full Description (6 bullets)

**Job Matching AI** | Personal Project | 2025
- Architected an intelligent job recommendation system using **LangGraph** to build a multi-step AI agent that orchestrates resume parsing, job searching, match analysis, and cover letter generation with stateful workflow management
- Implemented **RAG (Retrieval-Augmented Generation)** pipeline using LangChain and PostgreSQL pgvector, enabling semantic search across resume content with OpenAI Embeddings for context-aware job matching
- Developed adaptive matching algorithm that dynamically adjusts score thresholds (70→30) to guarantee 10 daily recommendations, achieving personalized job-resume compatibility analysis using GPT-4o-mini
- Built full-stack application with **FastAPI** backend and **React/TypeScript** frontend, featuring PDF resume upload, preference configuration (intern/sponsor status), and interactive daily task dashboard with completion tracking
- Engineered automated job discovery pipeline integrating LinkedIn API with APScheduler cron jobs, delivering daily email notifications at 7:00 AM EST with personalized cover letters for each matched position
- Leveraged **Claude Code** as AI-powered development assistant with custom **Claude Skills** for code review and deployment, utilizing **MCP (Model Context Protocol)** to integrate LinkedIn job search and Figma design tools for rapid prototyping and testing

---

### Option 2: Condensed Description (3 bullets)

**Job Matching AI** | Personal Project | 2025
- Built AI-powered job recommendation system using **LangGraph** for multi-step agent orchestration and **RAG** with pgvector for semantic resume-job matching, leveraging GPT-4o-mini for compatibility analysis
- Developed full-stack application with FastAPI/React/TypeScript featuring adaptive threshold algorithm that guarantees 10 daily job recommendations with auto-generated cover letters
- Implemented automated pipeline with LinkedIn API integration and scheduled email notifications, utilizing Docker containerization and Railway deployment for production infrastructure

---

### Option 3: One-liner (for skills section or brief mention)

**Job Matching AI**: LangGraph-based AI agent with RAG pipeline for automated job matching, cover letter generation, and daily email recommendations (FastAPI, React, PostgreSQL/pgvector, OpenAI)

---

## Skills to Highlight

Based on this project, you can claim proficiency in:

### AI/ML Engineering
- LangChain (RAG pipelines, document processing)
- LangGraph (stateful AI agents, workflow orchestration)
- OpenAI API (GPT-4o-mini, Embeddings)
- Prompt Engineering
- Vector Databases (pgvector)

### Backend Development
- Python (FastAPI, async programming)
- PostgreSQL (pgvector extension)
- SQLAlchemy ORM
- RESTful API design
- Task scheduling (APScheduler)

### Frontend Development
- React + TypeScript
- Tailwind CSS
- shadcn/ui components
- State management

### DevOps & Infrastructure
- Docker containerization
- Railway deployment
- CI/CD pipelines
- Environment management

### Protocols & Integrations
- MCP (Model Context Protocol) - LinkedIn & Figma integration
- LinkedIn API integration
- SendGrid email service

### AI-Assisted Development
- Claude Code (AI pair programming)
- Claude Skills (custom development workflows)
- Figma MCP (design-to-code integration)

---

## Interview Talking Points

### Q: Explain the LangGraph agent architecture

> "I built a multi-step AI agent using LangGraph that manages state across the entire job matching workflow. The agent starts by fetching the user's resume from our pgvector database using RAG, then searches LinkedIn for relevant positions. For each job, it calls GPT-4o-mini to analyze compatibility and generate a match score. The key innovation was implementing an adaptive threshold - if we don't get 10 matches at 70%, the agent automatically lowers the threshold in 5-point increments until we hit our target. Finally, it generates personalized cover letters and stores everything in PostgreSQL."

### Q: How does the RAG system work?

> "When a user uploads their PDF resume, I use LangChain's PyPDFLoader to extract text, then split it into chunks using RecursiveCharacterTextSplitter. Each chunk gets vectorized using OpenAI's text-embedding-ada-002 model and stored in PostgreSQL with the pgvector extension. When matching jobs, I perform a similarity search to retrieve the most relevant resume sections for that specific job description, giving the LLM precise context for analysis."

### Q: Why LangGraph over simple LangChain?

> "LangChain is great for simple chains, but our workflow required state management across multiple steps - we needed to track the current threshold, accumulated matches, and which jobs had been processed. LangGraph's StateGraph lets me define nodes (fetch_resume, search_jobs, analyze_match, generate_cover_letter) and edges (including conditional logic for the threshold adjustment), making the complex workflow maintainable and debuggable."

### Q: How did you handle the LinkedIn integration?

> "During development, I used MCP (Model Context Protocol) to quickly test LinkedIn searches within Claude Code. For production, I integrated the linkedin-api Python library directly into FastAPI, with credentials stored as environment variables on Railway. I implemented rate limiting to avoid API restrictions and added fallback error handling for network issues."

### Q: Explain the adaptive threshold algorithm

> "The goal was to always deliver exactly 10 job recommendations while prioritizing quality. I start with a 70-point threshold, score all jobs using GPT-4o-mini, and filter. If fewer than 10 jobs pass, I lower the threshold by 5 points and re-filter. This continues down to a floor of 30 points. The result is that users always get 10 recommendations - on good days they're all high-quality matches, on slower days they might include some stretch opportunities."

### Q: How did you use Claude Code and MCP in development?

> "I used Claude Code as my AI pair programming assistant throughout the project. I created custom Claude Skills - reusable instruction sets for code review, LangChain best practices, and deployment workflows. For rapid prototyping, I integrated MCP (Model Context Protocol) servers: LinkedIn MCP let me test job search queries directly in my development environment without writing API integration code first, and Figma MCP helped translate design mockups into React components. This AI-assisted workflow significantly accelerated development - I could iterate on features in minutes rather than hours."

---

## Metrics to Mention (Projected/Estimated)

- **10 daily job recommendations** guaranteed through adaptive threshold
- **7-day data retention** with automated cleanup
- **< 2 second** resume parsing and vectorization
- **95%+ email delivery rate** via SendGrid
- **Sub-100ms** vector similarity search with pgvector indexing

---

## Related Keywords for ATS

```
LangChain, LangGraph, RAG, Retrieval-Augmented Generation, OpenAI, GPT-4,
Large Language Models, LLM, AI Agent, Vector Database, pgvector, PostgreSQL,
FastAPI, Python, React, TypeScript, Tailwind CSS, REST API, Docker, Railway,
MCP, Model Context Protocol, Embeddings, Semantic Search, NLP,
Prompt Engineering, Full Stack, Async Programming, Cron Jobs, Email Automation,
Claude Code, Claude Skills, AI-Assisted Development, Figma, AI Pair Programming
```
