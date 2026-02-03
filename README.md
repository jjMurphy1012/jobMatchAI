# Job Matching AI

An intelligent job matching and recommendation system powered by **LangChain**, **LangGraph**, and **RAG** (Retrieval-Augmented Generation). The system automatically searches for relevant job positions, analyzes resume-job compatibility using AI, generates personalized cover letters, and delivers daily job recommendations.

> **Live Demo**: [https://jobmatchai-frontend-production.up.railway.app](https://welcoming-mindfulness-production-e40c.up.railway.app)

---

## Screenshots

### Dashboard Overview
Track your daily application goals and job matching progress at a glance.

![Overview Dashboard](docs/screenshots/overview.png)

### AI-Powered Job Matching
View AI-curated job opportunities with match scores, skill analysis, and personalized recommendations.

![Matched Jobs](docs/screenshots/matched-jobs.png)

### Resume Profile
Upload your PDF resume for AI-powered parsing and job matching.

![Resume Upload](docs/screenshots/resume-profile.png)

### Job Preferences
Configure your job search criteria including keywords, location, job type, and work preferences.

![Preferences](docs/screenshots/preferences.png)

### Backend Deployment (Railway)
Real-time deployment logs showing the FastAPI backend with LangGraph agent workflow.

![Railway Deployment](docs/screenshots/railway-logs.png)

---

## Features

- **Smart Resume Parsing**: Upload PDF resumes with automatic text extraction and semantic vectorization using OpenAI Embeddings
- **AI-Powered Job Matching**: LangGraph-based multi-step agent analyzes job-resume compatibility with adaptive threshold scoring
- **Personalized Cover Letters**: Auto-generated cover letters tailored to each job description using GPT-4o-mini
- **Skill Gap Analysis**: Identifies your strengths and skills to develop for each position
- **Daily Job Recommendations**: Scheduled job searches with email notifications at 7:00 AM EST
- **Interactive Task Dashboard**: Track daily application progress with completion status and motivational feedback
- **RAG Integration**: PostgreSQL with pgvector for persistent vector storage and semantic search
- **Mobile Responsive**: Fully responsive design with hamburger menu for mobile devices

---

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | Async Python web framework |
| LangChain | RAG pipeline and LLM orchestration |
| LangGraph | Multi-step AI agent with state management |
| PostgreSQL + pgvector | Relational database with vector storage |
| SQLAlchemy | Async ORM for database operations |
| APScheduler | Cron-based task scheduling |
| OpenAI API | GPT-4o-mini for analysis and generation |

### Frontend
| Technology | Purpose |
|------------|---------|
| React 18 | UI framework with hooks |
| TypeScript | Type-safe development |
| Tailwind CSS | Utility-first styling with glassmorphism design |
| Vite | Fast build tool and dev server |
| React Router | Client-side routing |
| Lucide Icons | Modern icon library |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Railway | Cloud deployment platform |
| Supabase | PostgreSQL with pgvector hosting |
| SendGrid | Email notification service (optional) |

---

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
│                           │  │  Job APIs  │    │   OpenAI     │  │ │
│                           │  │ (Remotive) │    │  GPT-4o-mini │  │ │
│                           │  └────────────┘    └──────────────┘  │ │
│                           └──────────────────────────────────────┘ │
│                                        │                           │
│                           ┌────────────▼────────────┐              │
│                           │  PostgreSQL + pgvector  │              │
│                           │       (Supabase)        │              │
│                           └─────────────────────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

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
│ Search Jobs     │  ← Remotive + Arbeitnow APIs
│ (20 positions)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analyze Match   │  ← GPT-4o-mini scoring
│ (per job)       │    + skill gap analysis
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
│ Save & Create   │  ← Daily tasks created
│ Daily Tasks     │
└────────┬────────┘
         │
         ▼
        END
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector extension (or Supabase account)
- OpenAI API Key

### Environment Variables

```bash
# Backend (.env)
OPENAI_API_KEY=sk-xxx
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Frontend (.env)
VITE_API_URL=http://localhost:8000
```

### Local Development

```bash
# Clone repository
git clone https://github.com/jjMurphy1012/jobMatchAI.git
cd jobMatchAI

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

---

## Deployment (Railway + Supabase)

### 1. Database Setup (Supabase)

1. Create a new project at [supabase.com](https://supabase.com)
2. Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Copy the Session Pooler connection string (port 5432)

### 2. Backend Deployment (Railway)

1. Connect your GitHub repository to Railway
2. Set Root Directory to `/backend`
3. Add environment variables:
   - `DATABASE_URL` - Supabase connection string (with `postgresql+asyncpg://` prefix)
   - `OPENAI_API_KEY` - Your OpenAI API key
4. Railway auto-deploys on git push

### 3. Frontend Deployment (Railway)

1. Create another service in Railway
2. Set Root Directory to `/frontend`
3. Add environment variable:
   - `VITE_API_URL` - Your backend Railway URL

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/resume` | Upload PDF resume |
| GET | `/api/resume` | Get parsed resume |
| DELETE | `/api/resume` | Delete resume |
| POST | `/api/preferences` | Set job preferences |
| GET | `/api/preferences` | Get job preferences |
| GET | `/api/jobs` | Get matched jobs |
| POST | `/api/jobs/refresh` | Trigger manual search |
| PUT | `/api/jobs/:id/apply` | Mark job as applied |
| GET | `/api/daily-tasks` | Get today's tasks |
| PUT | `/api/daily-tasks/:id/complete` | Mark task complete |
| GET | `/api/daily-tasks/stats` | Get completion stats |

---

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MATCH_THRESHOLD` | 70 | Initial matching score threshold |
| `MIN_THRESHOLD` | 30 | Minimum threshold floor |
| `TARGET_JOBS` | 10 | Target number of daily recommendations |
| `DATA_RETENTION_DAYS` | 7 | Days to retain job data |
| `PUSH_TIME` | 7:00 AM EST | Daily notification time |

---

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
│   │   │   ├── linkedin_service.py  # Job search APIs
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
├── docs/
│   └── screenshots/             # Project screenshots
├── docker-compose.yml
└── README.md
```

---

## Development Notes

### MCP Integration (Local Development)

For local development and testing, we utilized the Model Context Protocol (MCP) to integrate LinkedIn job search capabilities directly within the Claude Code development environment:

```bash
# Add LinkedIn MCP server
claude mcp add linkedin --transport stdio \
  --env LINKEDIN_EMAIL=your-email \
  --env LINKEDIN_PASSWORD=your-password \
  -- uvx --from git+https://github.com/adhikasp/mcp-linkedin mcp-linkedin
```

### Claude Code Integration

This project was developed with assistance from **Claude Code** (Anthropic's AI coding assistant), demonstrating:
- Rapid prototyping with AI pair programming
- MCP server integration for external API testing
- Automated code review and debugging

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.
