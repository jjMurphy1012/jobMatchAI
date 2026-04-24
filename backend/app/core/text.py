def normalize_company(value: str | None) -> str:
    """Canonical form for `Opportunity.company` / `InterviewExperience.company_name_normalized`
    matching. Writers and readers must share this function or matches silently break."""
    return " ".join((value or "").strip().lower().split())
