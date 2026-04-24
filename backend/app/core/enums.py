from typing import Final


class ApplicationStatus:
    SAVED: Final = "saved"
    APPLYING: Final = "applying"
    APPLIED: Final = "applied"
    INTERVIEWING: Final = "interviewing"
    OFFER: Final = "offer"
    REJECTED: Final = "rejected"
    WITHDRAWN: Final = "withdrawn"


# Statuses that mean the user has (at minimum) submitted — used by the UI
# to surface the "applied" flag on a match card.
APPLIED_STATUSES: Final = frozenset({
    ApplicationStatus.APPLYING,
    ApplicationStatus.APPLIED,
    ApplicationStatus.INTERVIEWING,
    ApplicationStatus.OFFER,
})


class ReviewStatus:
    DRAFT: Final = "draft"
    PUBLISHED: Final = "published"


REVIEW_STATUSES: Final = frozenset({ReviewStatus.DRAFT, ReviewStatus.PUBLISHED})


class UserRole:
    USER: Final = "user"
    ADMIN: Final = "admin"


USER_ROLES: Final = frozenset({UserRole.USER, UserRole.ADMIN})
