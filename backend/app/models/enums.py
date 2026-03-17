import enum


class ItemStatus(str, enum.Enum):
    NEW = "new"
    OK = "ok"
    BROKEN = "broken"
    LOST = "lost"
    REPAIRED = "repaired"
    SOLD = "sold"
    DISCARDED = "discarded"
    WANT = "want"
    IN_TRANSIT = "in_transit"
    NEEDS_REVIEW = "needs_review"


class LocationKind(str, enum.Enum):
    HOME = "home"
    FLAT = "flat"
    ROOM = "room"
    CLOSET = "closet"
    SHELF = "shelf"
    BOX = "box"
    GARAGE = "garage"
    OTHER = "other"


class Scope(str, enum.Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    GROUP = "group"


class TodoStatus(str, enum.Enum):
    OPEN = "open"
    DONE = "done"


class MediaType(str, enum.Enum):
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"


class UploadStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class AIDetectionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class AIDetectionDecision(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AIDetectionReviewAction(str, enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    LINK = "link_existing"
    CREATE = "create_new"
    FIX_LOCATION = "fix_location"
