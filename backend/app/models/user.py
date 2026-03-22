"""ORM-модели пользователя и workspace."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import Scope


class User(Base):
    """Пользователь системы.

    Представляет зарегистрированного пользователя приложения GdeMoe.
    Содержит информацию для аутентификации (email, хешированный пароль)
    и базовый профиль (полное имя, статус активности).

    Пользователь может владеть workspaces и быть членом других workspaces через Membership.

    Attributes:
        id (int): Уникальный идентификатор пользователя.
        email (str): Email-адрес пользователя, уникальный в системе.
        hashed_password (str): Хешированный пароль (bcrypt).
        full_name (str | None): Полное имя пользователя (опционально).
        is_active (bool): Флаг активности пользователя (по умолчанию True).
        created_at (datetime): Дата и время создания учетной записи.

    Relationships:
        workspaces: Workspaces, которыми владеет пользователь.
        memberships: Членства пользователя в workspaces.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workspaces = relationship("Workspace", back_populates="owner")
    memberships = relationship("Membership", back_populates="user")


class Workspace(Base):
    """Логическое пространство данных пользователя или группы.

    Workspace представляет изолированное пространство для хранения предметов,
    локаций и групп. Каждый пользователь имеет личный workspace, но может
    быть членом других workspaces для совместной работы.

    Attributes:
        id (int): Уникальный идентификатор workspace.
        name (str): Название workspace.
        scope (Scope): Уровень видимости (PRIVATE или PUBLIC).
        owner_user_id (int): ID владельца workspace.
        created_at (datetime): Дата и время создания workspace.

    Relationships:
        owner: Пользователь-владелец workspace.
        groups: Группы предметов в этом workspace.
        locations: Локации в этом workspace.
        items: Предметы в этом workspace.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[Scope] = mapped_column(
        Enum(Scope, values_callable=lambda x: [e.value for e in x]),
        default=Scope.PRIVATE,
    )
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="workspaces")
    groups = relationship("Group", back_populates="workspace")
    locations = relationship("Location", back_populates="workspace")
    items = relationship("Item", back_populates="workspace")
