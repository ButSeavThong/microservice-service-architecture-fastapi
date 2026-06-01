# app/models/profile.py

from sqlalchemy import String, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Profile(Base, UUIDMixin, TimestampMixin):
    """
    The core domain entity for profile-service.

    DESIGN DECISIONS:

    1. identity_id (not user_id):
       We deliberately call it identity_id to reinforce that
       this value comes from WSO2 Identity Server's `sub` claim.
       It's NOT a foreign key to another table — it's an external
       reference to an identity system we don't own.

    2. is_active flag:
       Never hard-delete profiles. When an account is deactivated,
       set is_active=False. This preserves audit history, supports
       recovery, and prevents orphaned references in other services.
       This is called "soft delete" pattern.

    3. Separate display_name from full_name:
       display_name: What the user wants others to see ("Th0ng")
       full_name: Legal/real name ("Thong Nguyen")
       Different use cases, different privacy rules.

    Spring Boot equivalent:
    This is your @Entity class. UUIDMixin = @GeneratedValue(UUID),
    TimestampMixin = @CreatedDate + @LastModifiedDate.

    __tablename__:
    Always explicit. Never rely on SQLAlchemy's auto-naming.
    In production teams, you need to know the exact table name
    for DBA queries, monitoring, and migrations.
    """

    __tablename__ = "profiles"

    # ── Identity (external reference) ────────────────────────
    identity_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="WSO2 JWT `sub` claim — external identity reference",
    )

    # ── Contact ───────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(320),      # RFC 5321 max email length
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Profile Info ──────────────────────────────────────────
    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(2048),     # Max URL length
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # ── Status ────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_onboarded: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True after user completes profile setup flow",
    )

    # ── Database-level constraints & indexes ──────────────────
    __table_args__ = (
        Index("ix_profiles_identity_id_active", "identity_id", "is_active"),
        # Composite index: most queries filter by both fields together.
        # e.g.: WHERE identity_id = 'user-123' AND is_active = true
        # A composite index is faster than two separate indexes for this pattern.
    )

    def __repr__(self) -> str:
        return (
            f"<Profile id={self.id!r} "
            f"identity_id={self.identity_id!r} "
            f"email={self.email!r}>"
        )