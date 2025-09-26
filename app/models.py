from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, BigInteger, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class FSTenant(Base):
    __tablename__ = "fs_tenant"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False)
    configuration = Column(JSONB, nullable=False)


class FSFiles(Base):
    __tablename__ = "fs_files"

    id = Column(String, primary_key=True)  # e.g., fs_023abx45
    user_id = Column(UUID(as_uuid=True), ForeignKey("fs_tenant.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    size = Column(BigInteger, nullable=False)
    media_type = Column(String, nullable=False)
    tag = Column(String, nullable=True)
    relative_path = Column(String, nullable=False)   # <-- NEW COLUMN
    file_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


