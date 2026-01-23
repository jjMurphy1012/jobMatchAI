from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Optional
import os

from app.core.config import settings
from app.models.models import Resume, ResumeChunk


class RAGService:
    """Service for RAG operations on resumes."""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model="text-embedding-ada-002"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    async def process_resume(
        self,
        file_path: str,
        resume_id: str,
        db: AsyncSession
    ) -> dict:
        """Process a PDF resume: extract text, chunk, and embed."""

        # 1. Load PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        # 2. Extract full text
        full_text = "\n".join([doc.page_content for doc in documents])

        # 3. Split into chunks
        chunks = self.text_splitter.split_text(full_text)

        # 4. Generate embeddings
        embeddings = await self.embeddings.aembed_documents(chunks)

        # 5. Store chunks with embeddings
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = ResumeChunk(
                resume_id=resume_id,
                content=chunk_text,
                embedding=embedding,
                chunk_index=i
            )
            db.add(chunk)

        # 6. Update resume with full content
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()
        if resume:
            resume.content = full_text
            # Store overall embedding (average of chunks)
            if embeddings:
                avg_embedding = [
                    sum(e[i] for e in embeddings) / len(embeddings)
                    for i in range(len(embeddings[0]))
                ]
                resume.embedding = avg_embedding

        return {
            "chunks_created": len(chunks),
            "content_preview": full_text[:500] if full_text else ""
        }

    async def get_relevant_context(
        self,
        query: str,
        db: AsyncSession,
        top_k: int = 3
    ) -> str:
        """Retrieve relevant resume chunks for a query using similarity search."""

        # Generate query embedding
        query_embedding = await self.embeddings.aembed_query(query)

        # Use pgvector similarity search
        # Note: This requires the vector extension and proper indexing
        sql = text("""
            SELECT content, 1 - (embedding <=> :query_embedding::vector) as similarity
            FROM resume_chunks
            ORDER BY embedding <=> :query_embedding::vector
            LIMIT :top_k
        """)

        result = await db.execute(
            sql,
            {"query_embedding": str(query_embedding), "top_k": top_k}
        )
        rows = result.fetchall()

        # Combine relevant chunks
        contexts = [row[0] for row in rows]
        return "\n\n".join(contexts)

    async def get_full_resume_text(self, db: AsyncSession) -> Optional[str]:
        """Get the full resume text content."""
        result = await db.execute(
            select(Resume).order_by(Resume.uploaded_at.desc()).limit(1)
        )
        resume = result.scalar_one_or_none()
        return resume.content if resume else None
