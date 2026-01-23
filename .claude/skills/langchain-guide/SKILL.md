---
name: langchain-guide
description: LangChain and LangGraph development best practices for this project
---

# LangChain & LangGraph Guide

## Project-Specific Implementations

### RAG Pipeline (Resume Processing)

```python
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector

# 1. Load PDF
loader = PyPDFLoader(file_path)
documents = loader.load()

# 2. Split text
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", " ", ""]
)
chunks = splitter.split_documents(documents)

# 3. Embed and store
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
vectorstore = PGVector.from_documents(
    documents=chunks,
    embedding=embeddings,
    connection=DATABASE_URL,
    collection_name=f"resume_{user_id}"
)
```

### LangGraph Agent Pattern

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Annotated
from operator import add

class AgentState(TypedDict):
    resume_text: str
    preferences: dict
    jobs: List[dict]
    matched_jobs: Annotated[List[dict], add]
    threshold: int
    messages: List[str]

def create_job_matching_agent():
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("fetch_context", fetch_context_node)
    workflow.add_node("search_jobs", search_jobs_node)
    workflow.add_node("analyze_match", analyze_match_node)
    workflow.add_node("adjust_threshold", adjust_threshold_node)
    workflow.add_node("generate_output", generate_output_node)

    # Add edges
    workflow.set_entry_point("fetch_context")
    workflow.add_edge("fetch_context", "search_jobs")
    workflow.add_edge("search_jobs", "analyze_match")

    # Conditional edge for threshold adjustment
    workflow.add_conditional_edges(
        "analyze_match",
        should_adjust_threshold,
        {
            "adjust": "adjust_threshold",
            "continue": "generate_output"
        }
    )
    workflow.add_edge("adjust_threshold", "analyze_match")
    workflow.add_edge("generate_output", END)

    return workflow.compile()
```

### OpenAI Integration

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000
)

# For structured output
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel

class MatchResult(BaseModel):
    score: int
    matched_skills: List[str]
    missing_skills: List[str]
    reason: str

parser = PydanticOutputParser(pydantic_object=MatchResult)
```

## Best Practices

### Error Handling

```python
from langchain.callbacks import get_openai_callback

async def safe_llm_call(prompt: str) -> str:
    try:
        with get_openai_callback() as cb:
            response = await llm.ainvoke(prompt)
            print(f"Tokens used: {cb.total_tokens}")
            return response.content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
```

### Prompt Templates

```python
from langchain.prompts import ChatPromptTemplate

match_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a professional career advisor."),
    ("human", """
    Analyze the match between this resume and job:

    Resume: {resume}
    Job: {job_description}

    Return JSON with: score (0-100), matched_skills, missing_skills, reason
    """)
])
```

### Memory Management

- Clear vector collections when user uploads new resume
- Use `pre_delete_collection=True` for updates
- Implement TTL for cached embeddings if needed

## Common Pitfalls

1. **Token Limits**: GPT-4o-mini has 128k context, but keep prompts reasonable
2. **Rate Limits**: Implement exponential backoff for API calls
3. **Cost Control**: Track token usage, set budget alerts
4. **Async**: Always use `ainvoke()` for async FastAPI routes
