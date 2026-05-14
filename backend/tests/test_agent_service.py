import pytest

from app.core.config import settings
from app.services.agent_service import JobMatchingAgent, _extract_json_payload


def test_extract_json_payload_from_markdown_array():
    payload = _extract_json_payload(
        """
Here is the ranking:
[
  {"index": 0, "score": 91}
]
"""
    )

    assert payload == [{"index": 0, "score": 91}]


def test_extract_json_payload_prefers_wrapped_object_before_inner_array():
    payload = _extract_json_payload(
        """
Result:
{"score": 82, "matched_skills": ["Python"], "missing_skills": []}
"""
    )

    assert payload == {"score": 82, "matched_skills": ["Python"], "missing_skills": []}


@pytest.mark.asyncio
async def test_analyze_matches_batches_llm_rerank(monkeypatch):
    monkeypatch.setattr(settings, "TARGET_JOBS", 2)
    monkeypatch.setattr(settings, "MATCH_LLM_RERANK_LIMIT", 3)
    monkeypatch.setattr(settings, "MATCH_LLM_BATCH_SIZE", 2)

    agent = object.__new__(JobMatchingAgent)
    seen_batches = []

    async def fake_score_job_batch(_resume, _profile_text, batch):
        seen_batches.append([job["title"] for job in batch])
        return [
            {
                "score": 80 + index,
                "reason": f"fit {job['title']}",
                "matched_skills": ["Python"],
                "missing_skills": [],
            }
            for index, job in enumerate(batch)
        ]

    agent._score_job_batch = fake_score_job_batch
    state = {
        "resume_text": "Python backend resume",
        "resume_embedding": None,
        "preferences": {"profile_text": "Backend roles"},
        "raw_jobs": [
            {"title": "A", "company": "Acme", "description": "Build APIs"},
            {"title": "B", "company": "Beta", "description": "Build systems"},
            {"title": "C", "company": "Core", "description": "Build platform"},
            {"title": "D", "company": "Delta", "description": "Not reranked"},
        ],
        "scored_jobs": [],
        "matched_jobs": [],
        "threshold": 70,
        "candidate_stats": {"scored_candidates": 4},
        "error": None,
    }

    result = await JobMatchingAgent._analyze_matches(agent, state)

    assert seen_batches == [["A", "B"], ["C"]]
    assert [job["title"] for job in result["scored_jobs"]] == ["B", "A", "C"]
    assert result["candidate_stats"]["llm_scored_candidates"] == 3
    assert result["candidate_stats"]["llm_batches"] == 2
