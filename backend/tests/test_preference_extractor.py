from app.services.preference_extractor import (
    PreferenceExtractorService,
    PreferenceFieldOverrides,
    PreferenceStructuredFields,
)


def test_fallback_extractor_handles_english_profile():
    service = PreferenceExtractorService()

    fields = service._fallback_extract(
        "I'm looking for mid-level backend or Go roles in NYC or remote. "
        "Need H1B sponsorship and want to avoid Meta. Salary target is 180k."
    )

    assert "Backend" in fields.keywords
    assert "Go" in fields.keywords
    assert "New York, NY" in fields.locations
    assert "Remote" in fields.locations
    assert fields.need_sponsor is True
    assert fields.experience_level == "mid"
    assert fields.remote_preference == "remote"
    assert fields.salary_min == 180000


def test_fallback_extractor_handles_chinese_profile():
    service = PreferenceExtractorService()

    fields = service._fallback_extract(
        "我想找纽约或者远程的后端岗位，需要H1B赞助，不考虑Meta，最好是中级工程师。"
    )

    assert "New York, NY" in fields.locations
    assert "Remote" in fields.locations
    assert fields.need_sponsor is True
    assert fields.experience_level == "mid"


def test_merge_fields_prefers_user_overrides():
    service = PreferenceExtractorService()
    extracted = PreferenceStructuredFields(
        keywords=["Backend"],
        locations=["New York, NY"],
        need_sponsor=False,
        remote_preference="onsite",
    )
    overrides = PreferenceFieldOverrides(
        keywords=["Backend", "Python"],
        need_sponsor=True,
        remote_preference="remote",
    )

    effective = service.merge_fields(extracted, overrides)

    assert effective.keywords == ["Backend", "Python"]
    assert effective.need_sponsor is True
    assert effective.remote_preference == "remote"
