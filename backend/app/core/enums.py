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
    NEEDS_REVIEW: Final = "needs_review"
    PUBLISHED: Final = "published"
    REJECTED: Final = "rejected"


REVIEW_STATUSES: Final = frozenset({
    ReviewStatus.DRAFT,
    ReviewStatus.NEEDS_REVIEW,
    ReviewStatus.PUBLISHED,
    ReviewStatus.REJECTED,
})


class UserRole:
    USER: Final = "user"
    ADMIN: Final = "admin"


USER_ROLES: Final = frozenset({UserRole.USER, UserRole.ADMIN})


class SourceType:
    GREENHOUSE: Final = "greenhouse"


SOURCE_TYPES: Final = frozenset({SourceType.GREENHOUSE})


class NotificationKind:
    DAILY_DIGEST: Final = "daily_digest"
    TEST: Final = "test"


class NotificationStatus:
    SENT: Final = "sent"
    FAILED: Final = "failed"
    SKIPPED: Final = "skipped"


class SourceSyncStatus:
    RUNNING: Final = "running"
    SUCCESS: Final = "success"
    FAILED: Final = "failed"


SOURCE_SYNC_STATUSES: Final = frozenset({
    SourceSyncStatus.RUNNING,
    SourceSyncStatus.SUCCESS,
    SourceSyncStatus.FAILED,
})
