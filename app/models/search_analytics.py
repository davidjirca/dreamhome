from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class SearchQuery(Base):
    """Model for tracking search queries for analytics"""
    __tablename__ = "search_queries"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # User tracking
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(100), nullable=True)  # For anonymous users

    # Search parameters
    search_text = Column(String(500), nullable=True, index=True)
    filters = Column(JSON, nullable=False)  # All search parameters as JSON

    # Search results
    result_count = Column(Integer, nullable=False)
    execution_time_ms = Column(Integer, nullable=True)

    # User interaction tracking
    clicked_property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True
    )
    clicked_at = Column(DateTime(timezone=True), nullable=True)

    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    referer = Column(String(500), nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    clicked_property = relationship("Property", foreign_keys=[clicked_property_id])

    def __repr__(self):
        return f"<SearchQuery {self.search_text or 'filtered'} - {self.result_count} results>"