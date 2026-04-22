from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
import logging
import re

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

EXTRACTION_VERSION = "profile-extractor-v1"

KNOWN_KEYWORDS = [
    "backend", "frontend", "full stack", "fullstack", "react", "typescript",
    "javascript", "python", "java", "go", "golang", "node", "node.js",
    "distributed systems", "distributed", "microservices", "data engineer",
    "data engineering", "machine learning", "ml", "ai", "platform",
    "devops", "cloud", "aws", "gcp", "sql", "postgres", "fastapi",
]

KNOWN_LOCATIONS = {
    "new york": "New York, NY",
    "nyc": "New York, NY",
    "boston": "Boston, MA",
    "seattle": "Seattle, WA",
    "austin": "Austin, TX",
    "san francisco": "San Francisco, CA",
    "sf": "San Francisco, CA",
    "bay area": "San Francisco Bay Area",
    "los angeles": "Los Angeles, CA",
    "remote": "Remote",
    "纽约": "New York, NY",
    "波士顿": "Boston, MA",
    "西雅图": "Seattle, WA",
    "奥斯汀": "Austin, TX",
    "旧金山": "San Francisco, CA",
    "远程": "Remote",
}

KNOWN_INDUSTRIES = [
    "fintech", "healthcare", "health tech", "ai", "saas", "e-commerce",
    "gaming", "robotics", "cybersecurity", "edtech",
]


class PreferenceStructuredFields(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    is_intern: bool = False
    need_sponsor: bool = False
    experience_level: Optional[Literal["entry", "mid", "senior"]] = None
    remote_preference: Optional[Literal["remote", "hybrid", "onsite"]] = None
    excluded_companies: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None


class PreferenceFieldOverrides(BaseModel):
    keywords: Optional[list[str]] = None
    locations: Optional[list[str]] = None
    is_intern: Optional[bool] = None
    need_sponsor: Optional[bool] = None
    experience_level: Optional[Literal["entry", "mid", "senior"]] = None
    remote_preference: Optional[Literal["remote", "hybrid", "onsite"]] = None
    excluded_companies: Optional[list[str]] = None
    industries: Optional[list[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None


class PreferenceAnalysisResult(BaseModel):
    extracted_fields: PreferenceStructuredFields
    effective_fields: PreferenceStructuredFields
    extraction_version: str = EXTRACTION_VERSION
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    used_fallback: bool = False


class PreferenceExtractorService:
    def __init__(self):
        self.llm = None
        if settings.OPENAI_API_KEY:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0,
            )

    async def analyze(
        self,
        raw_text: str,
        overrides: Optional[PreferenceFieldOverrides] = None,
    ) -> PreferenceAnalysisResult:
        extracted, used_fallback = await self._extract_fields(raw_text)
        effective = self.merge_fields(extracted, overrides)

        return PreferenceAnalysisResult(
            extracted_fields=extracted,
            effective_fields=effective,
            used_fallback=used_fallback,
        )

    def merge_fields(
        self,
        extracted: PreferenceStructuredFields,
        overrides: Optional[PreferenceFieldOverrides] = None,
    ) -> PreferenceStructuredFields:
        effective = extracted.model_copy(deep=True)

        if not overrides:
            return effective

        for field_name, value in overrides.model_dump(exclude_unset=True).items():
            setattr(effective, field_name, value)

        return self._normalize_fields(effective)

    def legacy_payload(self, effective: PreferenceStructuredFields, raw_text: str) -> dict[str, Any]:
        locations = effective.locations
        keywords = effective.keywords

        return {
            "keywords": ", ".join(keywords),
            "location": locations[0] if locations else None,
            "is_intern": effective.is_intern,
            "need_sponsor": effective.need_sponsor,
            "experience_level": effective.experience_level,
            "job_description": raw_text,
            "remote_preference": effective.remote_preference,
            "excluded_companies": effective.excluded_companies,
            "industries": effective.industries,
            "salary_min": effective.salary_min,
            "salary_max": effective.salary_max,
            "salary_currency": effective.salary_currency,
        }

    async def _extract_fields(self, raw_text: str) -> tuple[PreferenceStructuredFields, bool]:
        if self.llm:
            try:
                structured_llm = self.llm.with_structured_output(PreferenceStructuredFields)
                response = await structured_llm.ainvoke(
                    self._prompt(raw_text)
                )
                return self._normalize_fields(response), False
            except Exception as exc:
                logger.warning("Preference extraction fell back to heuristics: %s", exc)

        return self._fallback_extract(raw_text), True

    def _prompt(self, raw_text: str) -> str:
        return (
            "Extract a structured job search preference profile from the following text. "
            "The user may write in English or Chinese. Only infer what is strongly supported. "
            "Normalize repeated values, keep arrays short and high-signal, and use USD when salary currency "
            "is not explicit but clearly implies US compensation.\n\n"
            f"USER PROFILE:\n{raw_text}"
        )

    def _fallback_extract(self, raw_text: str) -> PreferenceStructuredFields:
        text = raw_text.lower()

        keywords = [item.title() for item in KNOWN_KEYWORDS if item in text]
        locations = [
            normalized
            for token, normalized in KNOWN_LOCATIONS.items()
            if token in text
        ]
        industries = [item.title() for item in KNOWN_INDUSTRIES if item in text]

        excluded_companies = []
        company_match = re.search(
            r"(exclude|avoid|not interested in|排除|不要)(.*?)(companies|company|公司|$)",
            raw_text,
            flags=re.IGNORECASE,
        )
        if company_match:
            excluded_companies = self._split_token_list(company_match.group(2))

        is_intern = any(token in text for token in ["intern", "internship", "实习"])
        need_sponsor = any(token in text for token in ["h1b", "sponsor", "sponsorship", "签证", "赞助"])

        experience_level = None
        if any(token in text for token in ["entry", "junior", "new grad", "graduate", "entry-level", "校招"]):
            experience_level = "entry"
        elif any(token in text for token in ["senior", "staff", "lead", "principal", "资深"]):
            experience_level = "senior"
        elif any(token in text for token in ["mid", "3 years", "4 years", "5 years", "中级"]):
            experience_level = "mid"

        remote_preference = None
        if any(token in text for token in ["remote", "远程"]):
            remote_preference = "remote"
        elif any(token in text for token in ["hybrid", "混合"]):
            remote_preference = "hybrid"
        elif any(token in text for token in ["onsite", "on-site", "现场", "坐班"]):
            remote_preference = "onsite"

        salary_min = None
        salary_max = None
        salary_currency = None
        salary_match = re.search(r"\$?\s*(\d{2,3})\s*[kK]", raw_text)
        salary_range_match = re.search(
            r"\$?\s*(\d{2,3})\s*(?:-|~|to)\s*\$?\s*(\d{2,3})\s*[kK]",
            raw_text,
            flags=re.IGNORECASE,
        )
        if salary_range_match:
            salary_min = int(salary_range_match.group(1)) * 1000
            salary_max = int(salary_range_match.group(2)) * 1000
            salary_currency = "USD"
        elif salary_match:
            salary_min = int(salary_match.group(1)) * 1000
            salary_currency = "USD"

        return self._normalize_fields(
            PreferenceStructuredFields(
                keywords=keywords,
                locations=locations,
                is_intern=is_intern,
                need_sponsor=need_sponsor,
                experience_level=experience_level,
                remote_preference=remote_preference,
                excluded_companies=excluded_companies,
                industries=industries,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=salary_currency,
            )
        )

    def _normalize_fields(self, fields: PreferenceStructuredFields) -> PreferenceStructuredFields:
        return PreferenceStructuredFields(
            keywords=self._dedupe(fields.keywords),
            locations=self._dedupe(fields.locations),
            is_intern=fields.is_intern,
            need_sponsor=fields.need_sponsor,
            experience_level=fields.experience_level,
            remote_preference=fields.remote_preference,
            excluded_companies=self._dedupe(fields.excluded_companies),
            industries=self._dedupe(fields.industries),
            salary_min=fields.salary_min,
            salary_max=fields.salary_max,
            salary_currency=fields.salary_currency,
        )

    def _dedupe(self, values: list[str]) -> list[str]:
        seen = set()
        normalized = []
        for value in values:
            cleaned = value.strip()
            if not cleaned:
                continue

            key = cleaned.lower()
            if key in seen:
                continue

            seen.add(key)
            normalized.append(cleaned)

        return normalized

    def _split_token_list(self, raw_value: str) -> list[str]:
        return [
            token.strip(" .,:;")
            for token in re.split(r"[,/|、，]", raw_value)
            if token.strip(" .,:;")
        ]
