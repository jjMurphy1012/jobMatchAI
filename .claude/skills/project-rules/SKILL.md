---
name: project-rules
description: Project coding standards and tech stack conventions for Job Matching AI
---

# Project: Job Matching AI

## Tech Stack

### Backend (Python)
- **Framework**: FastAPI with async/await
- **LLM**: OpenAI GPT-4o-mini
- **AI Framework**: LangChain + LangGraph
- **Database**: PostgreSQL + pgvector
- **ORM**: SQLAlchemy (async)
- **Scheduler**: APScheduler
- **LinkedIn**: linkedin-api library

### Frontend (TypeScript)
- **Framework**: React 18+
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **Routing**: React Router v6
- **HTTP Client**: fetch/axios

## Coding Standards

### Python
- Use type hints for all functions
- Async functions for I/O operations
- Pydantic models for request/response validation
- Follow PEP 8 style guide
- Use descriptive variable names

```python
# Good
async def get_matched_jobs(user_id: str, limit: int = 10) -> List[Job]:
    ...

# Bad
def get_jobs(id, l=10):
    ...
```

### TypeScript
- Use `interface` over `type` for objects
- Functional components with hooks
- Explicit return types for functions
- No `any` type unless absolutely necessary

```typescript
// Good
interface Job {
  id: string;
  title: string;
  company: string;
}

const JobCard: React.FC<{ job: Job }> = ({ job }) => {
  ...
};

// Bad
const JobCard = (props: any) => {
  ...
};
```

## File Naming

- Python: `snake_case.py`
- TypeScript: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- CSS: `kebab-case.css`

## API Design

- RESTful endpoints
- Use HTTP methods correctly (GET, POST, PUT, DELETE)
- Return consistent JSON structure:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

## Environment Variables

- Never commit `.env` files
- Use `.env.example` as template
- Access via `os.getenv()` in Python, `import.meta.env` in Vite

## Git Commit Messages

- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Keep subject line under 50 characters
- Reference issue numbers when applicable
