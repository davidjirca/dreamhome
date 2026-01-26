from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class PropertyPriceHistory(Base):
    """Price history tracking for properties"""
    __tablename__ = "property_price_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    
    old_price = Column(Numeric(12, 2), nullable=False)
    new_price = Column(Numeric(12, 2), nullable=False)
    price_change_percent = Column(Numeric(5, 2), nullable=False)
    
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationship
    property = relationship("Property", back_populates="price_history")
    
    def __repr__(self):
        return f"<PropertyPriceHistory property={self.property_id} change={self.price_change_percent}%>"


class EmailLog(Base):
    """Email sending log for tracking"""
    __tablename__ = "email_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    email_to = Column(String(255), nullable=False)
    email_type = Column(String(50), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    # Renamed from 'metadata' to 'email_metadata' to avoid SQLAlchemy reserved keyword
    email_metadata = Column('metadata', JSON, nullable=True)
    
    # Relationship
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<EmailLog {self.email_type} to {self.email_to} success={self.success}>"