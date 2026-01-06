from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geography
import uuid
import enum
from app.core.database import Base


class PropertyType(str, enum.Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    STUDIO = "studio"
    PENTHOUSE = "penthouse"
    VILLA = "villa"
    DUPLEX = "duplex"
    LAND = "land"
    COMMERCIAL = "commercial"


class PropertyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SOLD = "sold"
    RENTED = "rented"
    EXPIRED = "expired"


class ListingType(str, enum.Enum):
    SALE = "sale"
    RENT = "rent"


class Property(Base):
    """Property listing model"""
    __tablename__ = "properties"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Basic Info
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    property_type = Column(SQLEnum(PropertyType), nullable=False, index=True)
    listing_type = Column(SQLEnum(ListingType), nullable=False, index=True)
    status = Column(SQLEnum(PropertyStatus), default=PropertyStatus.DRAFT, nullable=False, index=True)

    # Pricing
    price = Column(Integer, nullable=False, index=True)  # Whole number prices in RON/EUR
    price_per_sqm = Column(Numeric(10, 2), nullable=True)  # Can have decimals (e.g., 1250.50)
    currency = Column(String(3), default="RON", nullable=False)
    negotiable = Column(Boolean, default=False, nullable=False)

    # Details (area in square meters - whole numbers)
    total_area = Column(Integer, nullable=False)
    usable_area = Column(Integer, nullable=True)
    rooms = Column(Integer, nullable=False, index=True)
    bedrooms = Column(Integer, nullable=False)
    bathrooms = Column(Integer, nullable=False)
    floor = Column(Integer, nullable=True)
    total_floors = Column(Integer, nullable=True)

    # Features
    year_built = Column(Integer, nullable=True)
    balconies = Column(Integer, default=0, nullable=False)
    parking_spots = Column(Integer, default=0, nullable=False)
    has_garage = Column(Boolean, default=False, nullable=False)
    has_terrace = Column(Boolean, default=False, nullable=False)
    has_garden = Column(Boolean, default=False, nullable=False)
    is_furnished = Column(Boolean, default=False, nullable=False)
    heating_type = Column(String(50), nullable=True)
    energy_rating = Column(String(10), nullable=True)

    # Location
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    county = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=True)
    neighborhood = Column(String(100), nullable=True)

    # Geolocation
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    location = Column(Geography(geometry_type='POINT', srid=4326), nullable=True)

    # Media (JSON array of URLs)
    photos = Column(JSON, default=list, nullable=False)
    main_photo = Column(String(500), nullable=True)
    photo_count = Column(Integer, default=0, nullable=False)

    # SEO & Metrics
    slug = Column(String(255), unique=True, nullable=False, index=True)
    view_count = Column(Integer, default=0, nullable=False)
    favorite_count = Column(Integer, default=0, nullable=False)

    # Full-text search vector (generated column from migration 003)
    # This is a GENERATED ALWAYS column, so we don't insert/update it directly
    search_vector = Column(TSVECTOR, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], backref="properties")
    price_history = relationship("PropertyPriceHistory", back_populates="property", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Property {self.title} ({self.city})>"