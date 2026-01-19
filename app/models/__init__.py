from app.models.user import User, UserRole
from app.models.property import Property, PropertyType, PropertyStatus, ListingType
from app.models.alerts import PropertyPriceHistory, EmailLog
from app.models.favorite import Favorite
from app.models.saved_search import SavedSearch, NotificationFrequency
from app.models.search_analytics import SearchQuery

Property.price_history = relationship(
    "PropertyPriceHistory",
    back_populates="property",
    cascade="all, delete-orphan"
)

__all__ = [
    "User", 
    "UserRole",
    "Property",
    "PropertyType",
    "PropertyStatus",
    "ListingType",
    "Favorite",
    "SavedSearch",
    "NotificationFrequency",
    "PropertyPriceHistory",
    "EmailLog",
    "SearchQuery"
]