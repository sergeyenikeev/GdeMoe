from app.db.base_class import Base  # noqa

# Импорт моделей для Alembic
from app.models.user import User, Workspace  # noqa
from app.models.group import Group, Membership, GroupItem  # noqa
from app.models.location import Location  # noqa
from app.models.item import Item  # noqa
from app.models.batch import ItemBatch  # noqa
from app.models.tag import Tag, ItemTag  # noqa
from app.models.relations import ItemRelation, ItemNote, ItemHistory  # noqa
from app.models.media import Media, ItemMedia, MediaUploadHistory  # noqa
from app.models.todo import Todo  # noqa
from app.models.ai import AIDetection, AIDetectionObject, AIDetectionCandidate, AIDetectionReview  # noqa
