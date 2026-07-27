from typing import Final


class ApplicationStatus:
    SAVED: Final = "saved"
    APPLYING: Final = "applying"
    APPLIED: Final = "applied"
    ASSESSMENT: Final = "assessment"
    INTERVIEWING: Final = "interviewing"
    OFFER: Final = "offer"
    REJECTED: Final = "rejected"
    WITHDRAWN: Final = "withdrawn"


APPLICATION_STATUSES: Final = frozenset({
    ApplicationStatus.SAVED,
    ApplicationStatus.APPLYING,
    ApplicationStatus.APPLIED,
    ApplicationStatus.ASSESSMENT,
    ApplicationStatus.INTERVIEWING,
    ApplicationStatus.OFFER,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
})


# Stages that imply the application was actually submitted. Used to stamp
# applied_at when a record reaches one of them without a recorded date.
SUBMITTED_STATUSES: Final = frozenset({
    ApplicationStatus.APPLIED,
    ApplicationStatus.ASSESSMENT,
    ApplicationStatus.INTERVIEWING,
    ApplicationStatus.OFFER,
    ApplicationStatus.REJECTED,
})


class ApplicationChannel:
    ONLINE: Final = "online"
    REFERRAL: Final = "referral"


APPLICATION_CHANNELS: Final = frozenset({
    ApplicationChannel.ONLINE,
    ApplicationChannel.REFERRAL,
})


class JobType:
    FULL_TIME: Final = "full_time"
    INTERNSHIP: Final = "internship"
    NEW_GRAD: Final = "new_grad"
    CONTRACT: Final = "contract"


JOB_TYPES: Final = frozenset({
    JobType.FULL_TIME,
    JobType.INTERNSHIP,
    JobType.NEW_GRAD,
    JobType.CONTRACT,
})


# Statuses that mean the user has (at minimum) submitted — used by the UI
# to surface the "applied" flag on a match card.
APPLIED_STATUSES: Final = frozenset({
    ApplicationStatus.APPLYING,
    ApplicationStatus.APPLIED,
    ApplicationStatus.ASSESSMENT,
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
