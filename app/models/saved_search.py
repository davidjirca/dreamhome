from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base


class NotificationFrequency(str, enum.Enum):
    """Notification frequency options"""
    IMMEDIATE = "immediate"  # Real-time notifications
    DAILY = "daily"          # Once per day digest
    WEEKLY = "weekly"        # Once per week digest
    DISABLED = "disabled"    # No notifications


class SavedSearch(Base):
    """User's saved search queries"""
    __tablename__ = "saved_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Search details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Search parameters (PropertySearchParams as JSON)
    filters = Column(JSON, nullable=False)
    
    # Notification settings
    email_notifications = Column(Boolean, default=True, nullable=False)
    notification_frequency = Column(String(20), default=NotificationFrequency.DAILY, nullable=False)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    result_count = Column(Integer, default=0, nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="saved_searches")
    
    def __repr__(self):
        return f"<SavedSearch '{self.name}' user={self.user_id}>"