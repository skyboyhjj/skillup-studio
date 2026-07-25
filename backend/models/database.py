"""SQLAlchemy 数据模型"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, Text, JSON, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import DATABASE_URL, DATABASE_URL_SYNC


class Base(DeclarativeBase):
    pass


# ===== 用户 =====
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    role = Column(String(32), default="registered", nullable=False)  # admin/registered
    contribution_level = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


# ===== 工作室 =====
class Studio(Base):
    __tablename__ = "studios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    visibility = Column(String(16), default="private")  # private/public
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("StudioMember", back_populates="studio", cascade="all, delete-orphan")


# ===== 工作室成员 =====
class StudioMember(Base):
    __tablename__ = "studio_members"

    studio_id = Column(UUID(as_uuid=True), ForeignKey("studios.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(32), default="member")  # owner/admin/member/viewer
    ai_depth_limit = Column(String(4), default="L2")
    ai_can_edit = Column(Boolean, default=False)
    ai_require_approval = Column(Boolean, default=True)
    ai_domain_scope = Column(JSON, nullable=True)
    ai_daily_limit = Column(Integer, default=20)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    studio = relationship("Studio", back_populates="members")
    user = relationship("User")


# ===== 规则库 =====
class RuleLibrary(Base):
    __tablename__ = "rule_libraries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_type = Column(String(32), nullable=False)  # admin/studio/user
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    domain = Column(String(64), nullable=False)
    rules_json = Column(JSONB, nullable=False, default=dict)
    version = Column(Integer, default=1)
    parent_library_id = Column(UUID(as_uuid=True), ForeignKey("rule_libraries.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


# ===== 社区分享 =====
class CommunityShare(Base):
    __tablename__ = "community_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    library_id = Column(UUID(as_uuid=True), ForeignKey("rule_libraries.id"), nullable=False)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSONB, default=list)
    license = Column(String(32), default="CC BY 4.0")
    forked_from = Column(UUID(as_uuid=True), ForeignKey("community_shares.id"), nullable=True)
    status = Column(String(16), default="pending")  # pending/approved/rejected
    is_curated = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)
    fork_count = Column(Integer, default=0)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    author = relationship("User", foreign_keys=[author_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


# ===== DSL 审计日志 =====
class DSLAuditLog(Base):
    __tablename__ = "dsl_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    library_id = Column(UUID(as_uuid=True), ForeignKey("rule_libraries.id"), nullable=False)
    command = Column(String(16), nullable=False)  # MAP/LEARN/CORRECT/LAYER/FLOW
    intent = Column(JSONB, nullable=False)
    result = Column(JSONB, nullable=True)
    snapshot = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ===== 数据库引擎 =====
async_engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

sync_engine = create_engine(DATABASE_URL_SYNC, echo=False)
SyncSessionLocal = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)


async def get_async_session() -> AsyncSession:
    """FastAPI 依赖注入：异步会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_session() -> Session:
    """同步会话（用于脚本/初始化）"""
    return SyncSessionLocal()


async def init_db():
    """创建所有表"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)