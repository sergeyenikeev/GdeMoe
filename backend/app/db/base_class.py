"""Базовый declarative-класс для всех ORM-моделей."""

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore
        """По умолчанию имя таблицы совпадает с именем класса в нижнем регистре."""
        return cls.__name__.lower()
