from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Numeric, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base

class AlertFrequency(str, enum.Enum):
    """Alert frequency enumeration"""
    INSTANT = "instant"  # Immediate email
    DAILY = "daily"      # Daily digest
    WEEKLY = "weekly"    # Weekly digest

class EmailLog(Base):
    """Model for tracking sent emails"""
    __tablename__ = "email_logs"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # User reference (optional, for tracking purposes)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Email details
    email_to = Column(String(255), nullable=False)
    email_type = Column(String(50), nullable=False, index=True)  # e.g., 'new_listing', 'price_drop', 'welcome'
    subject = Column(String(255), nullable=False)

    # Status
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    # Additional metadata (optional)
    metadata = Column(JSON, nullable=True)  # Store property IDs, search IDs, etc.

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<EmailLog {self.email_type} to {self.email_to} - {'success' if self.success else 'failed'}>"


class PropertyPriceHistory(Base):
    """Model for tracking property price changes"""
    __tablename__ = "property_price_history"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Property reference
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Price change details
    old_price = Column(Numeric(12, 2), nullable=False)
    new_price = Column(Numeric(12, 2), nullable=False)
    price_change_percent = Column(Numeric(5, 2), nullable=False)  # Negative for price drops

    # Timestamp
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    property = relationship("Property", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory property={self.property_id} {self.old_price}->{self.new_price} ({self.price_change_percent}%)>"