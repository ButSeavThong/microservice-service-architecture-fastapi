# app/db/base.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    The single SQLAlchemy DeclarativeBase for all ORM models.

    WHY a shared Base?
    Alembic's autogenerate scans all models registered under one
    Base. If you create multiple Bases, migrations become fragmented
    and unreliable.

    Spring Boot equivalent:
    This is like your @Entity base configuration in Spring Data JPA.
    """
    pass


class TimestampMixin:
    """
    Reusable mixin that adds created_at and updated_at to any model.

    WHY a mixin?
    Every production table needs audit timestamps. Repeating these
    columns in every model violates DRY and leads to inconsistency.

    In Spring Boot, this is equivalent to @CreatedDate / @LastModifiedDate
    from Spring Data Auditing — but we implement it explicitly here
    for full control.

    WHY timezone-aware UTC?
    Storing naive datetimes is a production bug waiting to happen.
    When your service runs in Singapore but your DB server is UTC,
    naive datetimes create silent data corruption. Always UTC.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDMixin:
    """
    Provides a UUID primary key.

    WHY UUID over integer auto-increment?
    In a distributed microservice system:
    - Auto-increment IDs are tied to one database sequence.
    - Two services cannot independently generate non-colliding IDs.
    - UUIDs can be generated anywhere — client, service, DB.
    - UUIDs don't leak business intelligence (record count, growth rate).

    WHY generate in Python, not DB?
    So that the ID is available immediately after object creation,
    before any DB round-trip. This matters for event publishing:
    you want the profile_id in the Kafka event before the DB commit.
    """

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )