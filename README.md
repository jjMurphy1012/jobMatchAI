# Job Matching AI

An intelligent job matching and recommendation system powered by LangChain, LangGraph, and RAG (Retrieval-Augmented Generation). The system automatically searches for relevant job positions, analyzes resume-job compatibility using AI, generates personalized cover letters, and delivers daily job recommendations via email.

## Features

- **Smart Resume Parsing**: Upload PDF resumes with automatic text extraction and semantic vectorization using OpenAI Embeddings
- **AI-Powered Job Matching**: LangGraph-based multi-step agent analyzes job-resume compatibility with adaptive threshold scoring
- **Personalized Cover Letters**: Auto-generated cover letters tailored to each job description using GPT-4o-mini
- **Daily Job Recommendations**: Scheduled job searches with email notifications at 7:00 AM EST
- **Interactive Task Dashboard**: Track daily application progress with completion status and motivational feedback
- **RAG Integration**: PostgreSQL with pgvector for persistent vector storage and semantic search

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | Async Python web framework |
| LangChain | RAG pipeline and LLM orchestration |
| LangGraph | Multi-step AI agent with state management |
| PostgreSQL + pgvector | Relational database with vector storage |
| SQLAlchemy | ORM for database operations |
| APScheduler | Cron-based task scheduling |
| OpenAI API | GPT-4o-mini for analysis and generation |

### Frontend
| Technology | Purpose |
|------------|---------|
| React | UI framework |
| TypeScript | Type-safe development |
| Tailwind CSS | Utility-first styling |
| shadcn/ui | Modern component library |
| React Router | Client-side routing |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Railway | Cloud deployment platform |
| SendGrid | Email notification service |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Job Matching AI System                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐         ┌──────────────────────────────────────┐ │
│  │   Frontend   │   API   │              Backend                 │ │
│  │    (React)   │◄───────►│            (FastAPI)                 │ │
│  └──────────────┘         │                                      │ │
│                           │  ┌────────────┐    ┌──────────────┐  │ │
│                           │  │ LangGraph  │    │ RAG System   │  │ │
│                           │  │   Agent    │◄──►│ (LangChain)  │  │ │
│                           │  └─────┬──────┘    └──────────────┘  │ │
│                           │        │                              │ │
│                           │        ▼                              │ │
│                           │  ┌────────────┐    ┌──────────────┐  │ │
│                           │  │ LinkedIn   │    │   OpenAI     │  │ │
│                           │  │    API     │    │  GPT-4o-mini │  │ │
│                           │  └────────────┘    └──────────────┘  │ │
│                           └──────────────────────────────────────┘ │
│                                        │                           │
│                           ┌────────────▼────────────┐              │
│                           │  PostgreSQL + pgvector  │              │
│                           └─────────────────────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## LangGraph Agent Workflow

```
START
  │
  ▼
┌─────────────────┐
│ Fetch Resume    │  ← RAG retrieval from pgvector
│ + Preferences   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Search Jobs     │  ← LinkedIn API integration
│ (20 positions)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analyze Match   │  ← GPT-4o-mini scoring
│ (per job)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Score >= 70?    │─No─►│ Lower threshold │
│ Count >= 10?    │     │ (70→65→60→...)  │
└────────┬────────┘     └────────┬────────┘
         │ Yes                   │
         ▼                       │
┌─────────────────┐◄─────────────┘
│ Generate Cover  │
│ Letters         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Save & Notify   │  ← Email via SendGrid
└────────┬────────┘
         │
         ▼
        END
```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector extension
- OpenAI API Key

### Environment Variables

```bash
# Backend (.env)
OPENAI_API_KEY=sk-xxx
DATABASE_URL=postgresql://user:pass@localhost:5432/jobmatch
LINKEDIN_EMAIL=your-email@example.com
LINKEDIN_PASSWORD=your-password
SENDGRID_API_KEY=SG.xxx

# Frontend (.env)
VITE_API_URL=http://localhost:8000
```

### MCP Integration (Local Development)

For local development and testing, we utilized the Model Context Protocol (MCP) to integrate LinkedIn job search capabilities directly within the Claude Code development environment:

```bash
# Add LinkedIn MCP server
claude mcp add linkedin --transport stdio \
  --env LINKEDIN_EMAIL=your-email \
  --env LINKEDIN_PASSWORD=your-password \
  -- uvx --from git+https://github.com/adhikasp/mcp-linkedin mcp-linkedin

# Verify configuration
claude mcp list
```

This enabled rapid prototyping and testing of job search queries before implementing the production linkedin-api integration.

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-username/job-matching-ai.git
cd job-matching-ai

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Deployment (Railway)

1. Connect GitHub repository to Railway
2. Create PostgreSQL database service
3. Add environment variables in Railway dashboard
4. Deploy backend and frontend as separate services

Railway will automatically:
- Detect Dockerfile and build containers
- Provision PostgreSQL with pgvector
- Generate public URLs for each service
- Handle SSL certificates

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/resume` | Upload PDF resume |
| GET | `/api/resume` | Get parsed resume |
| POST | `/api/preferences` | Set job preferences |
| GET | `/api/preferences` | Get job preferences |
| GET | `/api/jobs` | Get matched jobs |
| POST | `/api/jobs/refresh` | Trigger manual search |
| GET | `/api/daily-tasks` | Get today's tasks |
| PUT | `/api/daily-tasks/:id/complete` | Mark task complete |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MATCH_THRESHOLD` | 70 | Initial matching score threshold |
| `MIN_THRESHOLD` | 30 | Minimum threshold floor |
| `TARGET_JOBS` | 10 | Target number of daily recommendations |
| `DATA_RETENTION_DAYS` | 7 | Days to retain job data |
| `PUSH_TIME` | 7:00 AM EST | Daily notification time |

## Project Structure

```
job-matching-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── api/                 # API routes
│   │   ├── models/              # SQLAlchemy models
│   │   ├── services/
│   │   │   ├── rag_service.py   # RAG implementation
│   │   │   ├── agent_service.py # LangGraph agent
│   │   │   ├── linkedin_service.py
│   │   │   ├── email_service.py
│   │   │   └── scheduler_service.py
│   │   └── core/                # Config, database
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/               # React pages
│   │   ├── components/          # UI components
│   │   └── api/                 # API client
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .claude/
│   └── skills/                  # Claude Code skills
└── README.md
```

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.
